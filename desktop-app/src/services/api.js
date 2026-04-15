import axios from 'axios';

const getBaseUrl = () => {
  const savedUrl = localStorage.getItem('SHADOWFORGE_BACKEND_URL');
  return (savedUrl || import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000').replace(/\/$/, '') + '/api';
};

export const checkHealth = async () => {
  try {
    const response = await axios.get(`${getBaseUrl()}/health`, { timeout: 10000 });
    return response.data;
  } catch (error) {
    throw error;
  }
};

export const chatWithAI = async (messages, options = {}) => {
  try {
    const response = await axios.post(`${getBaseUrl()}/chat`, { 
      messages, 
      token: options.token,
      options: {
        sudo: options.sudo,
        api_keys: options.api_keys
      }
    });
    return response.data;
  } catch (error) {
    console.error("Chat API error:", error);
    throw error;
  }
};

export const searchAI = async (query, options = {}) => {
  try {
    const response = await axios.post(`${getBaseUrl()}/search`, { 
      query, 
      token: options.token, 
      messages: [],
      options: {
        api_keys: options.api_keys
      }
    });
    return response.data;
  } catch (error) {
    console.error("Search API error:", error);
    throw error;
  }
};
