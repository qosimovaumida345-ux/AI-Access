import axios from 'axios';
import { io } from 'socket.io-client';

let socket = null;
export const API_BASE_URL = process.env.EXPO_PUBLIC_API_BASE_URL || "http://192.168.1.100:5000";

export const initSocket = async (token) => {
  if (socket) return socket;
  // Initialize WebSocket for real-time exam answers
  socket = io(API_BASE_URL);
  
  socket.on('connect', () => {
    socket.emit('register', { token });
  });

  return socket;
};

export const analyzeScreenImage = async (imageBase64, token, prompt = "Solve the question shown. Reply ONLY with the brief, correct answer.") => {
  try {
    const res = await axios.post(`${API_BASE_URL}/api/screen`, {
      imageBase64,
      token,
      prompt
    });
    return res.data;
  } catch (error) {
    console.error("Screen analysis error:", error.message);
    throw error;
  }
};

export const chatWithAI = async (messages, token) => {
  try {
    const res = await axios.post(`${API_BASE_URL}/api/chat`, {
      messages,
      token
    });
    return res.data;
  } catch (error) {
    console.error("Chat error:", error.message);
    throw error;
  }
};
