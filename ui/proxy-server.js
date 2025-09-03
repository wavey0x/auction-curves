#!/usr/bin/env node

const express = require('express');
const { createProxyMiddleware } = require('http-proxy-middleware');
const cors = require('cors');

const app = express();
const PORT = process.env.PROXY_PORT || 3001;

// Enable CORS for all origins in development
app.use(cors());

// Parse JSON requests
app.use(express.json());

// Proxy middleware configuration
const proxyOptions = {
  target: 'https://eth.wavey.info',
  changeOrigin: true,
  secure: true,
  followRedirects: true,
  logLevel: 'info',
  auth: 'guest:guest', // Handle authentication
  onProxyReq: (proxyReq, req, res) => {
    // Log requests for debugging
    console.log(`Proxying: ${req.method} ${req.url}`);
  },
  onError: (err, req, res) => {
    console.error('Proxy error:', err);
    res.status(500).json({ 
      error: 'Proxy error', 
      message: err.message 
    });
  }
};

// Create proxy middleware
const proxy = createProxyMiddleware(proxyOptions);

// Use proxy for all requests
app.use('/', proxy);

app.listen(PORT, () => {
  console.log(`🚀 CORS Proxy Server running on http://localhost:${PORT}`);
  console.log(`🔗 Proxying to: https://eth.wavey.info`);
  console.log(`🔑 Using auth: guest:guest`);
});