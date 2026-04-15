const express = require('express');
const router = express.Router();
const axios = require('axios');
const { callWithFallback } = require('../ai');

// Extremely basic DuckDuckGo HTML scraper for lightweight search
async function basicSearch(query) {
  try {
    const res = await axios.get(`https://html.duckduckgo.com/html/?q=${encodeURIComponent(query)}`);
    const html = res.data;
    
    // Extract snippets using basic string manipulation (no cheerio to keep lightweight)
    const snippets = [];
    let match;
    const regex = /<a class="result__snippet[^>]*>(.*?)<\/a>/g;
    
    while ((match = regex.exec(html)) !== null && snippets.length < 5) {
      let text = match[1].replace(/<\/?[^>]+(>|$)/g, ""); // strip tags
      snippets.push(text);
    }
    
    return snippets.join('\n');
  } catch (e) {
    return "Search failed.";
  }
}

// POST /api/search
// AI decides if it needs to search, or app simply routes here.
router.post('/', async (req, res) => {
  const { query, messages } = req.body;
  if (!query) return res.status(400).json({ error: 'query is required' });

  try {
    // 1. Get search context
    const searchContext = await basicSearch(query);

    // 2. Synthesize with AI
    let finalMessages = messages || [];
    finalMessages.push({
      role: 'system',
      content: `Use the following search results to answer the user: \n${searchContext}`
    });
    finalMessages.push({ role: 'user', content: query });

    const result = await callWithFallback(finalMessages, { maxTokens: 1024 });
    res.json({ success: true, text: result.text, source: result.provider, rawSearch: searchContext });
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
});

module.exports = router;
