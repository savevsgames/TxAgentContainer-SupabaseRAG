/*
# Add metadata column to user_symptoms table

This migration adds the missing metadata column to the user_symptoms table
to match the application code expectations.

## Changes Made:
1. Add metadata JSONB column with default empty object
2. Ensure the column is nullable for backward compatibility

## Purpose:
- Fix the error: "Could not find the 'metadata' column of 'user_symptoms'"
- Align database schema with application code expectations
*/

-- Add the missing metadata column to user_symptoms table
ALTER TABLE public.user_symptoms 
ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'::JSONB;

-- Update any existing rows to have the default metadata value
UPDATE public.user_symptoms 
SET metadata = '{}'::JSONB 
WHERE metadata IS NULL;