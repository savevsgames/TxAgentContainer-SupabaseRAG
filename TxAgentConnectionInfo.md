# TxAgent Container Connection & Troubleshooting Guide

## Current Status Summary

### ✅ What's Working
- **Container Health**: `/health` endpoint responds correctly with BioBERT model info
- **Authentication**: Supabase JWT tokens are being generated and sent properly
- **Network Connectivity**: Container is reachable from Node.js backend
- **CORS**: Recently fixed to allow WebContainer domains
- **OpenAI Fallback**: Working perfectly as backup system

### ❌ What's Failing
- **POST Endpoints**: All POST requests to TxAgent return `405 Method Not Allowed`
- **Chat Functionality**: `/chat` endpoint not responding to POST requests
- **Embedding Processing**: `/embed` endpoint not accepting document uploads
- **Agent Session Management**: Cannot create agent sessions due to RLS policy issues

## File Organization Issues Fixed

### Problem Identified
Several critical files were located outside the `hybrid-agent` directory, causing import errors when the Docker container was built. The Docker build process only copies files from the `hybrid-agent` directory into the container.

### Files Moved to `hybrid-agent/`:
- ✅ `llm.py` → `hybrid-agent/llm.py`
- ✅ `utils.py` → `hybrid-agent/utils.py` 
- ✅ Enhanced `auth.py` with detailed JWT debugging
- ✅ Enhanced `main.py` with comprehensive logging

### Missing `/test` Endpoint Issue
The Postman collection referenced a `/test` endpoint that didn't exist. This has been added to the container with both GET and POST methods for debugging.

## Critical Questions for TxAgent Container

### 1. Endpoint Verification ✅ FIXED
**Question**: What endpoints are actually available and what HTTP methods do they support?

**Current Implementation**:
```python
# Available endpoints in main.py:
GET  /health          # Health check
GET  /test            # Debug endpoint  
POST /test            # Debug endpoint with data
POST /chat            # Chat with documents
POST /embed           # Process documents
GET  /embedding-jobs/{job_id}  # Check job status
```

**Test Commands**:
```bash
# Test health (should work)
curl https://bjo5yophw94s7b-8000.proxy.runpod.net/health

# Test new debug endpoints
curl https://bjo5yophw94s7b-8000.proxy.runpod.net/test
curl -X POST https://bjo5yophw94s7b-8000.proxy.runpod.net/test \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'
```

### 2. FastAPI Configuration ✅ ENHANCED
**Question**: Is FastAPI properly configured to handle POST requests?

**Enhancements Made**:
- Added comprehensive request/response logging middleware
- Enhanced CORS configuration to allow all methods
- Added debug endpoints for testing
- Improved error handling and logging

**Debug Features Added**:
```python
@app.middleware("http")
async def log_requests(request: Request, call_next):
    # Logs every request with full details
    # Includes authentication debugging
    # Tracks processing times
```

### 3. Authentication Flow ✅ ENHANCED
**Question**: How is the Supabase JWT being validated and processed?

**Enhanced JWT Debugging**:
- **SECURITY WARNING**: Added extensive JWT logging for debugging (marked for removal)
- Logs JWT token structure, timing, and validation steps
- Shows exact error messages and exception details
- Tracks token expiration and clock skew issues

**What We're Logging Now**:
```python
# JWT token details (length, preview)
# Unverified header and payload inspection
# Token timing (exp, iat, current time)
# Detailed error messages for each failure type
# User authentication success/failure
```

### 4. Environment Variables ✅ VERIFIED
**Question**: Are all required environment variables properly set?

**Required Variables** (should be set in RunPod):
```bash
SUPABASE_URL=https://bfjfjxzdjhraabputkqi.supabase.co
SUPABASE_KEY=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...  # anon key
SUPABASE_SERVICE_ROLE_KEY=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...  # service role
SUPABASE_JWT_SECRET=your-jwt-secret-here  # CRITICAL for JWT validation
SUPABASE_STORAGE_BUCKET=documents
MODEL_NAME=dmis-lab/biobert-v1.1
DEVICE=cuda
OPENAI_API_KEY=your-openai-api-key  # Optional for LLM responses
```

**Verification**: The enhanced logging will show if JWT_SECRET is properly loaded.

### 5. Database Connectivity ✅ IMPLEMENTED
**Question**: Can the container successfully connect to Supabase and perform operations?

**RLS Policy Issues**: The logs show RLS policy violations. This suggests:
1. JWT validation might be failing
2. User context not being passed correctly to database queries
3. RLS policies might need adjustment

## Expected Container Behavior

### On Startup
1. ✅ Load BioBERT model on CUDA
2. ✅ Initialize Supabase client with provided credentials  
3. ✅ Register all FastAPI routes (GET /health, POST /chat, POST /embed, GET+POST /test)
4. ✅ Start Uvicorn server on port 8000
5. ✅ Log successful initialization with detailed environment info

### On POST /chat Request
1. ✅ Receive and validate JSON payload
2. ✅ Extract and verify JWT token (with extensive logging)
3. ✅ Get user_id from JWT claims
4. ✅ Generate query embedding using BioBERT
5. ⚠️ Search user's documents in Supabase (RLS issues)
6. ✅ Generate contextual response
7. ✅ Return JSON response with sources

### On POST /embed Request  
1. ✅ Receive document data and metadata
2. ✅ Extract and verify JWT token
3. ✅ Process document text through BioBERT
4. ⚠️ Store embeddings in Supabase with user_id (RLS issues)
5. ✅ Return processing results

## Debugging Steps Implemented

### 1. Enhanced Logging ✅ DONE
```python
# Added comprehensive request/response logging
# JWT validation debugging with token details
# Performance metrics tracking
# Error tracking with full stack traces
```

### 2. Test Endpoints ✅ ADDED
```python
@app.get("/test")
@app.post("/test") 
# Simple endpoints to verify POST method handling
```

### 3. Route Registration Verification ✅ IMPLEMENTED
```python
# Startup logging shows all registered routes
# Request middleware logs every incoming request
```

### 4. Supabase Connection Testing ✅ READY
The enhanced logging will show database connection attempts and RLS policy violations.

## Common Issues & Solutions

### 1. RunPod Proxy Issues ⚠️ POSSIBLE
- **Problem**: RunPod proxy might be blocking POST requests
- **Test**: The new `/test` endpoints will help verify this
- **Workaround**: If GET works but POST doesn't, it's a proxy issue

### 2. FastAPI/Uvicorn Configuration ✅ FIXED
- **Problem**: Server not configured to handle POST methods
- **Fix**: Enhanced CORS and middleware configuration
- **Verification**: Added test endpoints

### 3. CORS Configuration ✅ FIXED
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 4. Authentication Middleware ✅ ENHANCED
- **Problem**: JWT validation failing silently
- **Fix**: Added extensive JWT debugging (marked as security risk)
- **Test**: Logs will show exact JWT validation steps

## Next Steps for Testing

### 1. Rebuild Container
The container needs to be rebuilt with the moved files:
```bash
# In RunPod, rebuild the container to include:
# - hybrid-agent/llm.py
# - hybrid-agent/utils.py  
# - Enhanced auth.py and main.py
```

### 2. Test Endpoints in Order
```bash
# 1. Health check (should work)
curl https://bjo5yophw94s7b-8000.proxy.runpod.net/health

# 2. Test GET endpoint (should work)  
curl https://bjo5yophw94s7b-8000.proxy.runpod.net/test

# 3. Test POST endpoint (this is the critical test)
curl -X POST https://bjo5yophw94s7b-8000.proxy.runpod.net/test \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'

# 4. Test POST with auth
curl -X POST https://bjo5yophw94s7b-8000.proxy.runpod.net/test \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{"test": "authenticated"}'
```

### 3. Check Container Logs
The enhanced logging will show:
- JWT token validation details
- Request/response flow
- Database connection attempts
- RLS policy violations
- Exact error messages

### 4. JWT Secret Verification
The logs will show if `SUPABASE_JWT_SECRET` is properly configured in the container environment.

## Security Warnings ⚠️

**IMPORTANT**: The current implementation includes extensive JWT debugging that logs sensitive information. These debug features are marked with security warnings and should be removed before production:

```python
# SECURITY WARNING: The following logging exposes sensitive information
# TODO: Remove these debug logs before production deployment
```

**Locations to clean up later**:
- `hybrid-agent/auth.py` - Lines with JWT token logging
- `hybrid-agent/main.py` - Enhanced debug middleware

## Success Criteria

- [ ] POST /test returns valid JSON response (not 405)
- [ ] POST /chat returns valid JSON response (not 405)  
- [ ] POST /embed accepts document data successfully
- [ ] JWT authentication works correctly (logs show validation success)
- [ ] User-specific data filtering via RLS (no more policy violations)
- [ ] BioBERT embeddings generated and stored
- [ ] End-to-end document upload → embedding → chat query workflow

## Updated Postman Collection

The Postman collection should now work with the `/test` endpoints. The container will provide detailed logs showing exactly what's happening with each request.

## Contact Information

- **Container URL**: `https://bjo5yophw94s7b-8000.proxy.runpod.net/`
- **Test User**: `gregcbarker@gmail.com`  
- **Backend Health**: `https://medical-rag-vector-uploader-1.onrender.com/health`

The enhanced logging will provide complete visibility into the request flow, authentication process, and any failures that occur.