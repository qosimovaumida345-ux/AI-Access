const express = require('express');
const router = express.Router();
const { callWithFallback } = require('../ai');

router.post('/', async (req, res) => {
  const { messages, options } = req.body;
  if (!messages || !Array.isArray(messages)) {
    return res.status(400).json({ error: 'messages array is required' });
  }

  try {
    const result = await callWithFallback(messages, options || {});
    res.json({ success: true, ...result });
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
});

module.exports = router;
