const Groq = require('groq-sdk');
const OpenAI = require('openai');
const { GoogleGenAI } = require('@google/genai');
const Anthropic = require('@anthropic-ai/sdk');
const axios = require('axios');

// Provider priority: free first
const PROVIDER_ORDER = ['groq', 'gemini', 'openrouter', 'together', 'mistral', 'cohere'];
const AVAILABLE_PROVIDERS = new Set(PROVIDER_ORDER);

function normalizeProviders(inputProviders) {
  if (!Array.isArray(inputProviders) || inputProviders.length === 0) return PROVIDER_ORDER;
  const normalized = inputProviders
    .map((p) => String(p || '').trim().toLowerCase())
    .filter((p) => AVAILABLE_PROVIDERS.has(p));
  return normalized.length ? normalized : PROVIDER_ORDER;
}

function normalizeMessages(messages) {
  if (!Array.isArray(messages)) return [];
  return messages
    .filter((m) => m && typeof m.content === 'string' && m.content.trim().length > 0)
    .map((m) => ({
      role: m.role === 'assistant' ? 'assistant' : 'user',
      content: m.content
    }));
}

async function callWithFallback(messages, options = {}) {
  const errors = [];
  const providers = normalizeProviders(options.providers);
  const safeMessages = normalizeMessages(messages);

  if (safeMessages.length === 0) {
    throw new Error('No valid messages provided');
  }

  for (const provider of providers) {
    try {
      const result = await callProvider(provider, safeMessages, options);
      return { text: result, provider };
    } catch (err) {
      console.warn(`[AI] ${provider} failed: ${err.message}`);
      errors.push({ provider, error: err.message });
    }
  }
  throw new Error(`All providers failed:\n${errors.map(e => `${e.provider}: ${e.error}`).join('\n')}`);
}

async function callProvider(provider, messages, options = {}) {
  const systemMsg = options.system || 'You are a helpful AI assistant.';
  const maxTokens = options.maxTokens || 2048;

  switch (provider) {
    case 'groq': {
      if (!process.env.GROQ_API_KEY) throw new Error('No Groq key');
      const groq = new Groq({ apiKey: process.env.GROQ_API_KEY });
      const res = await groq.chat.completions.create({
        model: 'llama-3.3-70b-versatile',
        messages: [{ role: 'system', content: systemMsg }, ...messages],
        max_tokens: maxTokens,
        temperature: 0.7,
      });
      return res?.choices?.[0]?.message?.content || '';
    }

    case 'gemini': {
      if (!process.env.GOOGLE_AI_API_KEY) throw new Error('No Gemini key');
      const ai = new GoogleGenAI({ apiKey: process.env.GOOGLE_AI_API_KEY });
      const prompt = messages.map(m => `${m.role === 'user' ? 'User' : 'Assistant'}: ${m.content}`).join('\n');
      const res = await ai.models.generateContent({
        model: 'gemini-2.5-flash',
        contents: prompt,
        config: { systemInstruction: systemMsg, maxOutputTokens: maxTokens }
      });
      return res?.text || '';
    }

    case 'openrouter': {
      if (!process.env.OPENROUTER_API_KEY) throw new Error('No OpenRouter key');
      const res = await axios.post('https://openrouter.ai/api/v1/chat/completions', {
        model: 'meta-llama/llama-3.3-70b-instruct:free',
        messages: [{ role: 'system', content: systemMsg }, ...messages],
        max_tokens: maxTokens,
      }, {
        headers: {
          Authorization: `Bearer ${process.env.OPENROUTER_API_KEY}`,
          'Content-Type': 'application/json',
          'HTTP-Referer': 'https://ai-access.app',
          'X-Title': 'AI-Access'
        }
      });
      return res?.data?.choices?.[0]?.message?.content || '';
    }

    case 'together': {
      if (!process.env.TOGETHER_API_KEY) throw new Error('No Together key');
      const res = await axios.post('https://api.together.xyz/v1/chat/completions', {
        model: 'meta-llama/Llama-3.3-70B-Instruct-Turbo-Free',
        messages: [{ role: 'system', content: systemMsg }, ...messages],
        max_tokens: maxTokens,
      }, {
        headers: { Authorization: `Bearer ${process.env.TOGETHER_API_KEY}` }
      });
      return res?.data?.choices?.[0]?.message?.content || '';
    }

    case 'mistral': {
      if (!process.env.MISTRAL_API_KEY) throw new Error('No Mistral key');
      const res = await axios.post('https://api.mistral.ai/v1/chat/completions', {
        model: 'mistral-small-latest',
        messages: [{ role: 'system', content: systemMsg }, ...messages],
        max_tokens: maxTokens,
      }, {
        headers: { Authorization: `Bearer ${process.env.MISTRAL_API_KEY}` }
      });
      return res?.data?.choices?.[0]?.message?.content || '';
    }

    case 'cohere': {
      if (!process.env.COHERE_API_KEY) throw new Error('No Cohere key');
      const userMsg = messages[messages.length - 1].content;
      const res = await axios.post('https://api.cohere.com/v2/chat', {
        model: 'command-r-plus',
        messages: [
          { role: 'system', content: systemMsg },
          ...messages
        ],
      }, {
        headers: {
          Authorization: `Bearer ${process.env.COHERE_API_KEY}`,
          'Content-Type': 'application/json'
        }
      });
      return res?.data?.message?.content?.[0]?.text || '';
    }

    default:
      throw new Error(`Unknown provider: ${provider}`);
  }
}

// Vision-capable providers only
async function callVision(imageBase64, prompt) {
  // Try Gemini first (free), then OpenRouter vision model
  const errors = [];

  // 1) Gemini vision
  if (process.env.GOOGLE_AI_API_KEY) {
    try {
      const ai = new GoogleGenAI({ apiKey: process.env.GOOGLE_AI_API_KEY });
      const cleanBase64 = imageBase64.replace(/^data:image\/\w+;base64,/, '');
      const res = await ai.models.generateContent({
        model: 'gemini-2.5-flash',
        contents: [
          prompt,
          { inlineData: { data: cleanBase64, mimeType: 'image/png' } }
        ]
      });
      return { text: res.text, provider: 'gemini' };
    } catch (e) {
      errors.push(`gemini: ${e.message}`);
    }
  }

  // 2) OpenRouter vision
  if (process.env.OPENROUTER_API_KEY) {
    try {
      const dataUrl = imageBase64.startsWith('data:') ? imageBase64 : `data:image/png;base64,${imageBase64}`;
      const res = await axios.post('https://openrouter.ai/api/v1/chat/completions', {
        model: 'google/gemini-flash-1.5',
        messages: [{ role: 'user', content: [
          { type: 'text', text: prompt },
          { type: 'image_url', image_url: { url: dataUrl } }
        ]}],
      }, {
        headers: {
          Authorization: `Bearer ${process.env.OPENROUTER_API_KEY}`,
          'Content-Type': 'application/json',
          'HTTP-Referer': 'https://ai-access.app',
        }
      });
      return { text: res.data.choices[0].message.content, provider: 'openrouter' };
    } catch (e) {
      errors.push(`openrouter: ${e.message}`);
    }
  }

  throw new Error(`Vision failed: ${errors.join(', ')}`);
}

module.exports = { callWithFallback, callProvider, callVision };
