/**
 * Provenance Logger - Node.js Dashboard
 * Lightweight Express server that proxies Python Flask API
 */

const express = require('express');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 8080;
const API_URL = process.env.API_URL || 'http://localhost:5000';

// Serve static files
app.use(express.static(path.join(__dirname, 'public')));

// API proxy endpoint (optional - can also call API directly from browser)
app.get('/api/*', async (req, res) => {
  try {
    const apiPath = req.path.replace('/api/', '');
    const url = `${API_URL}/api/${apiPath}`;

    const response = await fetch(url);
    const data = await response.json();

    res.json(data);
  } catch (error) {
    console.error('API proxy error:', error);
    res.status(500).json({ error: 'API request failed' });
  }
});

// Health check
app.get('/health', (req, res) => {
  res.json({ status: 'ok', service: 'provenance-logger-ui' });
});

// Start server
app.listen(PORT, '0.0.0.0', () => {
  console.log(`Provenance Logger Dashboard running on http://0.0.0.0:${PORT}`);
  console.log(`API endpoint: ${API_URL}`);
});
