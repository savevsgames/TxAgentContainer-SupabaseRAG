import sys
import os
import unittest
from unittest.mock import patch, MagicMock
import torch
import numpy as np

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from embedder import Embedder

class TestEmbedder(unittest.TestCase):
    """Test cases for the Embedder class."""
    
    @patch('embedder.AutoTokenizer')
    @patch('embedder.AutoModel')
    @patch('embedder.create_client')
    def setUp(self, mock_create_client, mock_auto_model, mock_auto_tokenizer):
        """Set up test fixtures."""
        # Mock tokenizer and model
        self.mock_tokenizer = MagicMock()
        mock_auto_tokenizer.from_pretrained.return_value = self.mock_tokenizer
        
        self.mock_model = MagicMock()
        mock_model_instance = MagicMock()
        self.mock_model_output = MagicMock()
        self.mock_hidden_states = torch.zeros((1, 10, 768))
        self.mock_model_output.last_hidden_state = self.mock_hidden_states
        mock_model_instance.return_value = self.mock_model_output
        self.mock_model.__call__ = mock_model_instance
        mock_auto_model.from_pretrained.return_value = self.mock_model
        
        # Mock Supabase client
        self.mock_supabase = MagicMock()
        self.mock_storage = MagicMock()
        self.mock_bucket = MagicMock()
        self.mock_bucket.download.return_value = b"Test document content"
        self.mock_storage.from_.return_value = self.mock_bucket
        self.mock_supabase.storage = self.mock_storage
        
        self.mock_table = MagicMock()
        self.mock_insert = MagicMock()
        self.mock_execute = MagicMock()
        self.mock_execute.execute.return_value = MagicMock(data=[{"id": "test-id"}])
        self.mock_insert.insert.return_value = self.mock_execute
        self.mock_table.table.return_value = self.mock_insert
        self.mock_supabase.table = self.mock_table
        
        mock_create_client.return_value = self.mock_supabase
        
        # Initialize embedder
        self.embedder = Embedder()
        
    def test_extract_text_from_pdf(self):
        """Test extracting text from PDF content."""
        with patch('embedder.fitz.open') as mock_fitz_open:
            # Mock PDF document
            mock_pdf = MagicMock()
            mock_page = MagicMock()
            mock_page.get_text.return_value = "Test PDF content"
            mock_pdf.__enter__.return_value = mock_pdf
            mock_pdf.__iter__.return_value = [mock_page]
            mock_fitz_open.return_value = mock_pdf
            
            # Test extraction
            result = self.embedder._extract_text_from_pdf(b"test pdf content")
            self.assertEqual(result, "Test PDF content")
            
    def test_extract_text_from_docx(self):
        """Test extracting text from DOCX content."""
        with patch('embedder.docx.Document') as mock_docx:
            # Mock DOCX document
            mock_doc = MagicMock()
            mock_para1 = MagicMock()
            mock_para1.text = "Test DOCX"
            mock_para2 = MagicMock()
            mock_para2.text = "content"
            mock_doc.paragraphs = [mock_para1, mock_para2]
            mock_docx.return_value = mock_doc
            
            # Test extraction
            result = self.embedder._extract_text_from_docx(b"test docx content")
            self.assertEqual(result, "Test DOCX\ncontent\n")
            
    def test_split_text(self):
        """Test splitting text into chunks."""
        text = " ".join(["word"] * 1000)
        chunks = self.embedder._split_text(text)
        
        # Check number of chunks based on chunk_size and chunk_overlap
        expected_chunks = (1000 // (512 - 50)) + (1 if 1000 % (512 - 50) > 0 else 0)
        self.assertEqual(len(chunks), expected_chunks)
        
    @patch('torch.no_grad')
    def test_create_embedding(self, mock_no_grad):
        """Test creating embedding for text."""
        # Mock tokenizer input
        self.mock_tokenizer.return_value = {"input_ids": torch.zeros((1, 10))}
        
        # Mock model output
        embedding = self.embedder._create_embedding("Test text")
        
        # Check embedding dimension
        self.assertEqual(len(embedding), 768)
        
    def test_download_file(self):
        """Test downloading a file from Supabase Storage."""
        result = self.embedder._download_file("test.pdf")
        
        # Check if Supabase storage was called correctly
        self.mock_storage.from_.assert_called_once()
        self.mock_bucket.download.assert_called_once_with("test.pdf")
        
        # Check result
        self.assertEqual(result, b"Test document content")
        
    def test_process_document_pdf(self):
        """Test processing a PDF document."""
        with patch.object(self.embedder, '_extract_text_from_pdf', return_value="Test PDF content"):
            with patch.object(self.embedder, '_split_text', return_value=["Chunk 1", "Chunk 2"]):
                with patch.object(self.embedder, '_create_embedding', return_value=[0.1] * 768):
                    document_chunks = self.embedder.process_document(
                        "test.pdf",
                        {"title": "Test Document"}
                    )
                    
                    # Check number of chunks
                    self.assertEqual(len(document_chunks), 2)
                    
                    # Check first chunk content
                    self.assertEqual(document_chunks[0]["content"], "Chunk 1")
                    
                    # Check embedding dimension
                    self.assertEqual(len(document_chunks[0]["embedding"]), 768)
                    
                    # Check metadata
                    self.assertEqual(document_chunks[0]["metadata"]["title"], "Test Document")
                    self.assertEqual(document_chunks[0]["metadata"]["chunk_index"], 0)
                    self.assertEqual(document_chunks[0]["metadata"]["total_chunks"], 2)
                    
    def test_store_embeddings(self):
        """Test storing embeddings in Supabase."""
        document_chunks = [
            {
                "content": "Chunk 1",
                "embedding": [0.1] * 768,
                "metadata": {"title": "Test"}
            },
            {
                "content": "Chunk 2",
                "embedding": [0.2] * 768,
                "metadata": {"title": "Test"}
            }
        ]
        
        document_ids = self.embedder.store_embeddings(document_chunks, "user123")
        
        # Check if Supabase table was called correctly
        self.assertEqual(self.mock_table.table.call_count, 2)
        self.assertEqual(self.mock_insert.insert.call_count, 2)
        
        # Check document IDs
        self.assertEqual(document_ids, ["test-id", "test-id"])

if __name__ == '__main__':
    unittest.main()