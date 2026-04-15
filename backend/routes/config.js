const express = require('express');
const router = express.Router();
const fs = require('fs');
const path = require('path');

// Simple key-value store for device bindings
// In a real database, you'd store DeviceToken -> DefaultSettings
// For this app, we rely directly on the backend's .env for keys.
// So this config configures the *client* settings rather than the API keys.
const configStore = {};

router.get('/status', (req, res) => {
  res.json({
    hasGroq: !!process.env.GROQ_API_KEY,
    hasGemini: !!process.env.GOOGLE_AI_API_KEY,
    hasOpenRouter: !!process.env.OPENROUTER_API_KEY,
    hasTogether: !!process.env.TOGETHER_API_KEY,
    hasMistral: !!process.env.MISTRAL_API_KEY,
    hasCohere: !!process.env.COHERE_API_KEY
  });
});

router.post('/bind', (req, res) => {
  const { deviceToken, settings } = req.body;
  if (!deviceToken) return res.status(400).json({ error: 'deviceToken required' });
  
  configStore[deviceToken] = { ...(configStore[deviceToken] || {}), ...settings };
  res.json({ success: true, settings: configStore[deviceToken] });
});

router.get('/settings/:token', (req, res) => {
  const { token } = req.params;
  res.json({ success: true, settings: configStore[token] || {} });
});

module.exports = router;
