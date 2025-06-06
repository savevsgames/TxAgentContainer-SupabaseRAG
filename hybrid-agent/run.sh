#!/bin/bash
set -e

# Check environment variables
if [ -z "$SUPABASE_URL" ]; then
  echo "Error: SUPABASE_URL is not set"
  exit 1
fi

if [ -z "$SUPABASE_KEY" ]; then
  echo "Error: SUPABASE_KEY is not set"
  exit 1
fi

if [ -z "$SUPABASE_JWT_SECRET" ]; then
  echo "Error: SUPABASE_JWT_SECRET is not set"
  exit 1
fi

# Check CUDA availability
echo "Checking CUDA availability..."
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
if [ $? -ne 0 ]; then
  echo "Warning: CUDA check failed"
fi

# Set default device if not provided
if [ -z "$DEVICE" ]; then
  if python -c "import torch; print(torch.cuda.is_available())" | grep -q "True"; then
    export DEVICE="cuda"
  else
    export DEVICE="cpu"
    echo "Warning: CUDA not available, using CPU instead"
  fi
fi

# Optionally download model in advance
if [ "$PRELOAD_MODEL" = "true" ]; then
  echo "Preloading model..."
  python -c "from transformers import AutoTokenizer, AutoModel; model_name = 'dmis-lab/biobert-v1.1'; tokenizer = AutoTokenizer.from_pretrained(model_name); model = AutoModel.from_pretrained(model_name)"
fi

# Start the API server
echo "Starting TxAgent Hybrid Container..."
exec uvicorn main:app --host ${HOST:-0.0.0.0} --port ${PORT:-8000} --workers ${WORKERS:-1} --log-level ${LOG_LEVEL:-info}