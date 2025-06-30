/*
# Add user_symptoms table with metadata column

This migration adds the user_symptoms table for health tracking with proper RLS policies,
indexes, and triggers. It safely handles existing objects to avoid conflicts.

## Changes Made:
1. Create user_symptoms table with metadata column
2. Enable RLS with user isolation policy
3. Add performance indexes
4. Create updated_at trigger function and trigger
5. Grant proper permissions

## Safety Features:
- Uses IF NOT EXISTS for safe creation
- Drops existing triggers before recreating
- Handles existing functions gracefully
*/

-- Create user_symptoms table
CREATE TABLE IF NOT EXISTS public.user_symptoms (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  symptom_name TEXT NOT NULL,
  severity INTEGER CHECK (severity >= 1 AND severity <= 10),
  description TEXT,
  triggers TEXT[],
  duration_hours INTEGER,
  location TEXT,
  metadata JSONB DEFAULT '{}'::JSONB,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- Enable RLS
ALTER TABLE public.user_symptoms ENABLE ROW LEVEL SECURITY;

-- Drop existing policy if it exists and create new one
DROP POLICY IF EXISTS "user_symptoms_user_isolation" ON public.user_symptoms;
CREATE POLICY "user_symptoms_user_isolation" ON public.user_symptoms
  FOR ALL TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS user_symptoms_user_id_idx ON public.user_symptoms(user_id);
CREATE INDEX IF NOT EXISTS user_symptoms_created_at_idx ON public.user_symptoms(created_at);
CREATE INDEX IF NOT EXISTS user_symptoms_symptom_name_idx ON public.user_symptoms(symptom_name);
CREATE INDEX IF NOT EXISTS user_symptoms_severity_idx ON public.user_symptoms(severity);
CREATE INDEX IF NOT EXISTS user_symptoms_user_id_created_at_idx ON public.user_symptoms(user_id, created_at);

-- Create or replace the updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Drop existing trigger if it exists, then create new one
DROP TRIGGER IF EXISTS update_user_symptoms_updated_at ON public.user_symptoms;
CREATE TRIGGER update_user_symptoms_updated_at 
    BEFORE UPDATE ON public.user_symptoms 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Grant permissions
GRANT ALL ON public.user_symptoms TO authenticated;