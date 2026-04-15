require('dotenv').config();
const express = require('express');
const cors = require('cors');
const http = require('http');
const { Server } = require('socket.io');
const multer = require('multer');
const path = require('path');

const chatRouter = require('./routes/chat');
const screenRouter = require('./routes/screen');
const configRouter = require('./routes/config');
const searchRouter = require('./routes/search');

const app = express();
const server = http.createServer(app);
const io = new Server(server, { cors: { origin: '*' } });

// Expose io globally for routes
app.set('io', io);

app.use(cors());
app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ extended: true, limit: '50mb' }));

// ─── Routes ────────────────────────────────────────────
app.use('/api/config', configRouter);
app.use('/api/chat', chatRouter);
app.use('/api/screen', screenRouter);
app.use('/api/search', searchRouter);

// Health check
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', version: '1.0.0', timestamp: Date.now() });
});

// ─── WebSocket (Real-time exam mode) ────────────────────
const rooms = {}; // token -> socket.id

io.on('connection', (socket) => {
  console.log('[WS] Connected:', socket.id);

  socket.on('register', ({ token }) => {
    socket.join(token);
    rooms[token] = socket.id;
    console.log(`[WS] Device registered: token=${token}`);
  });

  socket.on('disconnect', () => {
    console.log('[WS] Disconnected:', socket.id);
  });
});

// ─── Start ───────────────────────────────────────────────
const PORT = process.env.PORT || 5000;
server.listen(PORT, () => {
  console.log(`\n🚀 AI-Access Backend running on port ${PORT}`);
  console.log(`   Providers loaded:`);
  if (process.env.GROQ_API_KEY)        console.log('   ✅ Groq');
  if (process.env.GOOGLE_AI_API_KEY)   console.log('   ✅ Gemini');
  if (process.env.OPENROUTER_API_KEY)  console.log('   ✅ OpenRouter');
  if (process.env.TOGETHER_API_KEY)    console.log('   ✅ Together AI');
  if (process.env.MISTRAL_API_KEY)     console.log('   ✅ Mistral');
  if (process.env.COHERE_API_KEY)      console.log('   ✅ Cohere');
  if (process.env.HUGGINGFACE_API_KEY) console.log('   ✅ HuggingFace');
  console.log('');
});
