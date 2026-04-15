const express = require('express');
const router = express.Router();
const { callVision } = require('../ai');

// POST /api/screen
router.post('/', async (req, res) => {
  const { imageBase64, prompt } = req.body;
  
  if (!imageBase64) {
    return res.status(400).json({ error: 'imageBase64 is required' });
  }

  const analyzePrompt = prompt || "Solve the question in this image. Give ONLY the correct answer. Be as brief and accurate as possible. No formatting or extra text.";

  try {
    const result = await callVision(imageBase64, analyzePrompt);
    
    // Broadcast the result to the connected WS clients (for overlay Exam Mode)
    const io = req.app.get('io');
    const token = req.headers['x-device-token'] || req.body.token;
    if (io && token) {
      io.to(token).emit('exam_result', { text: result.text });
    }

    res.json({ success: true, ...result });
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
});

module.exports = router;
