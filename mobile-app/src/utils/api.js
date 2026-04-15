import axios from 'axios';
import { io } from 'socket.io-client';

import AsyncStorage from '@react-native-async-storage/async-storage';

let socket = null;
const DEFAULT_URL = "http://192.168.1.100:5000";

const getBaseUrl = async () => {
  const savedUrl = await AsyncStorage.getItem('SHADOWFORGE_BACKEND_URL');
  return savedUrl || DEFAULT_URL;
};

export const checkHealth = async () => {
  try {
    const baseUrl = await getBaseUrl();
    const res = await axios.get(`${baseUrl}/api/health`, { timeout: 10000 });
    return res.data;
  } catch (error) {
    throw error;
  }
};

export const initSocket = async (token) => {
  if (socket) return socket;
  const baseUrl = await getBaseUrl();
  socket = io(baseUrl);
  
  socket.on('connect', () => {
    socket.emit('register', { token });
  });

  return socket;
};

export const analyzeScreenImage = async (imageBase64, token, options = {}) => {
  try {
    const baseUrl = await getBaseUrl();
    const res = await axios.post(`${baseUrl}/api/screen`, {
      imageBase64,
      token,
      prompt: options.prompt || "Solve the question shown. Reply ONLY with the brief, correct answer.",
      options: {
        api_keys: options.api_keys
      }
    });
    return res.data;
  } catch (error) {
    console.error("Screen analysis error:", error.message);
    throw error;
  }
};

export const chatWithAI = async (messages, token, options = {}) => {
  try {
    const baseUrl = await getBaseUrl();
    const res = await axios.post(`${baseUrl}/api/chat`, {
      messages,
      token,
      options: {
        api_keys: options.api_keys
      }
    });
    return res.data;
  } catch (error) {
    console.error("Chat error:", error.message);
    throw error;
  }
};
