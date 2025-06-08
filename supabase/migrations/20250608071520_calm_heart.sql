/*
  # Create test medical document

  1. New Function
    - `create_test_medical_document` - Creates a test medical document with Morgellons disease information
  
  2. Security
    - Function uses SECURITY INVOKER to respect RLS policies
    - Only authenticated users can execute the function
*/

-- Create a function to insert a test medical document
CREATE OR REPLACE FUNCTION create_test_medical_document()
RETURNS UUID
LANGUAGE plpgsql
SECURITY INVOKER
AS $$
DECLARE
  doc_id UUID;
  test_embedding VECTOR(768);
BEGIN
  -- Generate a random embedding vector (this is just for testing)
  SELECT array_agg(random()::float)::vector(768) INTO test_embedding
  FROM generate_series(1, 768);
  
  -- Insert the test document
  INSERT INTO documents (
    id,
    content,
    embedding,
    metadata,
    user_id,
    created_at
  ) VALUES (
    gen_random_uuid(),
    'Morgellons disease is a rare and controversial condition characterized by the presence of fibers or other solid materials emerging from skin lesions, accompanied by symptoms such as crawling sensations on and under the skin. First described in 2002, patients report colorful, thread-like fibers and other materials protruding from their skin, along with sensations of crawling, biting, and stinging. While the CDC conducted a study in 2012 concluding that Morgellons was psychosomatic in nature (a form of delusional parasitosis), recent research has identified potential connections to Borrelia spirochetes, suggesting a possible link to Lyme disease. Some researchers have found unusual fibers containing cellulose, which is not naturally produced by the human body, as well as other unusual materials with unique spectral characteristics. Treatment approaches vary widely, from antipsychotic medications to long-term antibiotic regimens, with limited consensus on effective protocols. The condition remains poorly understood, with patients often experiencing significant psychological distress due to both symptoms and medical dismissal.',
    test_embedding,
    jsonb_build_object(
      'title', 'Rare Medical Conditions: Morgellons Disease',
      'author', 'Dr. Sarah Johnson',
      'category', 'dermatology',
      'year', '2024',
      'source', 'Journal of Investigative Dermatology',
      'test_document', true
    ),
    auth.uid(),
    now()
  ) RETURNING id INTO doc_id;
  
  RETURN doc_id;
END;
$$;

-- Grant execute permission to authenticated users
GRANT EXECUTE ON FUNCTION create_test_medical_document() TO authenticated;

-- Add comment explaining the function
COMMENT ON FUNCTION create_test_medical_document() IS 
'Creates a test medical document about Morgellons disease with a random embedding vector. 
The document is created for the authenticated user and respects RLS policies.';