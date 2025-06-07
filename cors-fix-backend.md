# CORS Fix for Node.js Backend

## The Problem

Your frontend (`https://medical-rag-vector-uploader-1.onrender.com`) cannot reach your backend (`https://medical-rag-vector-uploader.onrender.com`) due to CORS policy blocking the requests.

## The Solution

Add this CORS configuration to your Node.js backend:

```javascript
// In your main server.js or app.js file
const cors = require('cors');

// Configure CORS to allow your frontend domain
app.use(cors({
  origin: [
    'https://medical-rag-vector-uploader-1.onrender.com',  // Your frontend domain
    'https://medical-rag-vector-uploader.onrender.com',   // Your backend domain (for self-requests)
    'http://localhost:3000',  // For local development
    'http://localhost:5173',  // For Vite dev server
  ],
  credentials: true,
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
  allowedHeaders: [
    'Content-Type', 
    'Authorization', 
    'X-Requested-With',
    'Accept',
    'Origin'
  ],
  exposedHeaders: ['Content-Length', 'X-Foo', 'X-Bar'],
  maxAge: 86400 // 24 hours
}));

// Handle preflight requests explicitly
app.options('*', cors());
```

## Alternative: Environment-Based Configuration

```javascript
// More flexible approach using environment variables
const allowedOrigins = process.env.ALLOWED_ORIGINS 
  ? process.env.ALLOWED_ORIGINS.split(',')
  : [
      'https://medical-rag-vector-uploader-1.onrender.com',
      'http://localhost:3000',
      'http://localhost:5173'
    ];

app.use(cors({
  origin: function (origin, callback) {
    // Allow requests with no origin (like mobile apps or curl requests)
    if (!origin) return callback(null, true);
    
    if (allowedOrigins.indexOf(origin) !== -1) {
      callback(null, true);
    } else {
      callback(new Error('Not allowed by CORS'));
    }
  },
  credentials: true,
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization', 'X-Requested-With', 'Accept', 'Origin']
}));
```

## Environment Variable

Add this to your Render environment variables:

```
ALLOWED_ORIGINS=https://medical-rag-vector-uploader-1.onrender.com,http://localhost:3000,http://localhost:5173
```

## Quick Test

After deploying the CORS fix, test with curl:

```bash
curl -X OPTIONS https://medical-rag-vector-uploader.onrender.com/api/chat \
  -H "Origin: https://medical-rag-vector-uploader-1.onrender.com" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type,Authorization" \
  -v
```

You should see these headers in the response:
- `Access-Control-Allow-Origin: https://medical-rag-vector-uploader-1.onrender.com`
- `Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS`
- `Access-Control-Allow-Headers: Content-Type, Authorization, X-Requested-With, Accept, Origin`

## Debugging CORS Issues

Add this middleware to log CORS requests:

```javascript
app.use((req, res, next) => {
  console.log(`CORS Debug: ${req.method} ${req.path}`);
  console.log('Origin:', req.headers.origin);
  console.log('Headers:', req.headers);
  next();
});
```

This will help you see exactly what requests are being made and from which origins.