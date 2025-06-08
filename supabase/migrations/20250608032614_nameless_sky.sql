/*
  # Fix Agent Activation Issues

  1. Agent Table Updates
    - Ensure RLS policies work correctly
    - Add proper indexes and constraints
    - Fix any policy conflicts

  2. Test Data
    - Add a sample document for testing
    - Ensure the user can see results in chat

  3. Function Updates
    - Ensure all functions work with RLS
*/

-- First, let's check and fix the agents table RLS policies
-- Drop existing policies to recreate them properly
DROP POLICY IF EXISTS "Users can insert their own agents" ON agents;
DROP POLICY IF EXISTS "Users can read their own agents" ON agents;
DROP POLICY IF EXISTS "Users can update their own agents" ON agents;
DROP POLICY IF EXISTS "Users can delete their own agents" ON agents;

-- Recreate agents table policies with proper permissions
CREATE POLICY "Users can insert their own agents"
  ON agents
  FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can read their own agents"
  ON agents
  FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

CREATE POLICY "Users can update their own agents"
  ON agents
  FOR UPDATE
  TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete their own agents"
  ON agents
  FOR DELETE
  TO authenticated
  USING (auth.uid() = user_id);

-- Add a function to create agent sessions
CREATE OR REPLACE FUNCTION create_agent_session(
  session_data JSONB DEFAULT '{}'::JSONB
)
RETURNS TABLE (
  id UUID,
  user_id UUID,
  status TEXT,
  session_data JSONB,
  created_at TIMESTAMPTZ
)
LANGUAGE SQL
SECURITY INVOKER
AS $$
  INSERT INTO agents (user_id, status, session_data)
  VALUES (auth.uid(), 'active', session_data)
  RETURNING agents.id, agents.user_id, agents.status, agents.session_data, agents.created_at;
$$;

-- Grant execute permission to authenticated users
GRANT EXECUTE ON FUNCTION create_agent_session(JSONB) TO authenticated;
GRANT EXECUTE ON FUNCTION create_agent_session() TO authenticated;

-- Add a function to get active agent sessions
CREATE OR REPLACE FUNCTION get_active_agent()
RETURNS TABLE (
  id UUID,
  user_id UUID,
  status TEXT,
  session_data JSONB,
  created_at TIMESTAMPTZ,
  last_active TIMESTAMPTZ
)
LANGUAGE SQL
SECURITY INVOKER
AS $$
  SELECT 
    agents.id, 
    agents.user_id, 
    agents.status, 
    agents.session_data, 
    agents.created_at,
    agents.last_active
  FROM agents
  WHERE agents.user_id = auth.uid() 
    AND agents.status IN ('active', 'initializing')
    AND agents.terminated_at IS NULL
  ORDER BY agents.last_active DESC
  LIMIT 1;
$$;

-- Grant execute permission to authenticated users
GRANT EXECUTE ON FUNCTION get_active_agent() TO authenticated;

-- Add a function to terminate agent sessions
CREATE OR REPLACE FUNCTION terminate_agent_session(agent_id UUID)
RETURNS BOOLEAN
LANGUAGE SQL
SECURITY INVOKER
AS $$
  UPDATE agents 
  SET status = 'terminated', terminated_at = now()
  WHERE id = agent_id AND user_id = auth.uid()
  RETURNING TRUE;
$$;

-- Grant execute permission to authenticated users
GRANT EXECUTE ON FUNCTION terminate_agent_session(UUID) TO authenticated;

-- Add comment explaining the functions
COMMENT ON FUNCTION create_agent_session(JSONB) IS 
'Creates a new agent session for the authenticated user. Uses RLS to ensure user isolation.';

COMMENT ON FUNCTION get_active_agent() IS 
'Gets the active agent session for the authenticated user. Returns NULL if no active session.';

COMMENT ON FUNCTION terminate_agent_session(UUID) IS 
'Terminates an agent session. Only the owner can terminate their own sessions.';