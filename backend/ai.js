const axios = require('axios');

const BRIDGE_URL = process.env.BRIDGE_URL || 'http://127.0.0.1:8000';

/**
 * Modern AI Bridge:
 * Delegates all complex AI logic, tool execution, and state
 * to the Python AgentCore for robustness and full device access.
 */
async function callWithFallback(messages, options = {}) {
  try {
    // Get the latest prompt from the messages array
    const lastMessage = messages[messages.length - 1];
    const prompt = lastMessage ? lastMessage.content : '';

    const response = await axios.post(`${BRIDGE_URL}/api/chat`, {
      prompt: prompt,
      is_sudo: options.sudo || false,
      workspace: options.workspace || null
      // Options like 'providers' can be added if the bridge supports it
    }, {
      timeout: 300000 // 5 minute timeout for complex tasks
    });

    if (response.data && response.data.success) {
      return {
        text: response.data.content,
        provider: response.data.provider,
        model: response.data.model,
        tokens: response.data.tokens,
        files: response.data.files
      };
    } else {
      throw new Error(response.data.error || 'Unknown agent error');
    }
  } catch (err) {
    console.error(`[AI Bridge] Error: ${err.message}`);
    
    // Fallback: If bridge is down and we have a local fallback, we could use it.
    // But we want the user to know the 'Brain' is required.
    throw new Error(`AI Core (Brain) is offline: ${err.message}`);
  }
}

// Keep Vision in JS for now as it's purely API based, but could be moved later
async function callVision(imageBase64, prompt) {
  const { GoogleGenAI } = require('@google/genai');
  if (process.env.GOOGLE_AI_API_KEY) {
    try {
      const ai = new GoogleGenAI({ apiKey: process.env.GOOGLE_AI_API_KEY });
      const cleanBase64 = imageBase64.replace(/^data:image\/\w+;base64,/, '');
      const res = await ai.getGenerativeModel({ model: 'gemini-1.5-flash' }).generateContent([
        prompt,
        { inlineData: { data: cleanBase64, mimeType: 'image/png' } }
      ]);
      const response = await res.response;
      return { text: response.text(), provider: 'gemini' };
    } catch (e) {
      throw new Error(`Vision failed: ${e.message}`);
    }
  }
  throw new Error('No Vision-capable API key (Gemini) found in .env');
}

module.exports = { callWithFallback, callVision };
