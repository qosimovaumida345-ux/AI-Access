import axios from 'axios';

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000').replace(/\/$/, '') + '/api';

export const chatWithAI = async (messages, token) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/chat`, { messages, token });
    return response.data;
  } catch (error) {
    console.error("Chat API error:", error);
    throw error;
  }
};

export const searchAI = async (query, token) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/search`, { query, token, messages: [] });
    return response.data;
  } catch (error) {
    console.error("Search API error:", error);
    throw error;
  }
};
