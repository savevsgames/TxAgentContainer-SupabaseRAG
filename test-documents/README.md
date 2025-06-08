# Test Documents for TxAgent Medical RAG System

This directory contains test medical documents for evaluating the TxAgent Medical RAG System's document processing, embedding, and retrieval capabilities.

## Available Test Documents

### 1. Morgellons Disease (morgellons-disease.md)

A comprehensive overview of Morgellons disease, a rare and controversial condition characterized by the presence of fibers emerging from skin lesions and unusual sensory symptoms.

**Key Information:**
- Detailed symptom descriptions
- Scientific controversy surrounding the condition
- Treatment approaches
- Research challenges
- Recent developments
- References to scientific literature

This document is particularly useful for testing the system's ability to:
1. Process and embed markdown files
2. Handle medical terminology
3. Retrieve relevant information about rare conditions
4. Answer questions about controversial medical topics

### Usage Instructions

When testing with these documents:

1. Upload the document to Supabase Storage through the frontend or API
2. Use the `/embed` endpoint to process and embed the document
3. Test the `/chat` endpoint with queries related to the document content
4. Verify that the system retrieves relevant information and generates accurate responses

## Adding New Test Documents

When adding new test documents to this directory:

1. Use clear, descriptive filenames
2. Include a variety of medical topics and document formats (PDF, DOCX, MD, TXT)
3. Update this README with information about the new document
4. Consider adding specific test queries for each document

## Test Queries for Morgellons Disease

Here are some example queries to test with the Morgellons disease document:

- "What is Morgellons disease?"
- "What are the symptoms of Morgellons disease?"
- "Is Morgellons disease controversial? Why?"
- "What treatments are available for Morgellons disease?"
- "What does recent research suggest about Morgellons disease?"
- "Is there a connection between Morgellons and Lyme disease?"
- "What unusual materials have been found in Morgellons patients?"
- "Why do Morgellons patients experience psychological distress?"