/*
  # Add embedding_jobs table and update documents table

  1. New Tables
    - `embedding_jobs`
      - `id` (uuid, primary key)
      - `file_path` (text)
      - `status` (text)
      - `metadata` (jsonb)
      - `chunk_count` (integer)
      - `error` (text)
      - `user_id` (uuid)
      - `created_at` (timestamptz)
      - `updated_at` (timestamptz)

  2. Security
    - Enable RLS on `embedding_jobs` table
    - Add policies for authenticated users to:
      - Insert their own jobs
      - Read their own jobs
      - Update their own jobs
*/

-- Create embedding_jobs table
CREATE TABLE IF NOT EXISTS embedding_jobs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  file_path text NOT NULL,
  status text NOT NULL DEFAULT 'pending',
  metadata jsonb DEFAULT '{}'::jsonb,
  chunk_count integer DEFAULT 0,
  error text,
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- Enable RLS
ALTER TABLE embedding_jobs ENABLE ROW LEVEL SECURITY;

-- Create index on user_id for faster lookups
CREATE INDEX IF NOT EXISTS embedding_jobs_user_id_idx ON embedding_jobs(user_id);

-- Create index on status for filtering
CREATE INDEX IF NOT EXISTS embedding_jobs_status_idx ON embedding_jobs(status);

-- Create policies for embedding_jobs table
CREATE POLICY "Users can insert their own embedding jobs"
  ON embedding_jobs
  FOR INSERT
  TO public
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can read their own embedding jobs"
  ON embedding_jobs
  FOR SELECT
  TO public
  USING (auth.uid() = user_id);

CREATE POLICY "Users can update their own embedding jobs"
  ON embedding_jobs
  FOR UPDATE
  TO public
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);