import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Sparkles, 
  MessageSquare, 
  FolderSearch, 
  Code2, 
  Image as ImageIcon, 
  Music, 
  Settings, 
  Maximize,
  Send,
  Loader2
} from 'lucide-react';
import FileBrowser from './FileBrowser';
import CodeWorkspace from './CodeWorkspace';
import MediaStudio from './MediaStudio';
import { chatWithAI } from './services/api';

export default function App() {
  const [activeTab, setActiveTab] = useState('chat');
  const [token, setToken] = useState('NOT_BOUND');
  const [messages, setMessages] = useState([{ role: 'system', content: 'AI-Access is fully integrated. How can I assist you today?' }]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [status, setStatus] = useState('Idle');
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim()) return;
    const newMsg = { role: 'user', content: input };
    const chatHistory = [...messages, newMsg];
    setMessages(chatHistory);
    setInput('');
    setIsTyping(true);
    setStatus('Sending');

    try {
      const res = await chatWithAI(chatHistory.filter(m => m.role !== 'system'), token);
      setMessages([...chatHistory, { role: 'assistant', content: res.text }]);
      setStatus(`Provider: ${res.provider || 'unknown'}`);
    } catch (e) {
      setMessages([...chatHistory, { role: 'assistant', content: "ERROR: Connection to AI Core failed. Is the backend running?" }]);
      setStatus('Failed');
    } finally {
      setIsTyping(false);
    }
  };

  const closeApp = () => window.electronAPI && window.electronAPI.hideWindow();
  const minimizeApp = () => window.electronAPI && window.electronAPI.minimizeWindow();
  const maximizeApp = () => window.electronAPI && window.electronAPI.maximizeWindow();
  const submitToken = () => window.electronAPI && window.electronAPI.setToken(token);

  const NavItem = ({ id, icon: Icon, label }) => (
    <button 
      onClick={() => setActiveTab(id)} 
      className={`group flex items-center justify-center w-14 h-14 rounded-2xl transition-all duration-300 ${
        activeTab === id 
          ? 'bg-gradient-to-tr from-indigo-500/20 to-purple-500/20 text-indigo-400 shadow-[0_0_15px_rgba(99,102,241,0.2)]' 
          : 'text-slate-500 hover:text-slate-300 hover:bg-white/5'
      }`}
      title={label}
    >
      <Icon size={24} strokeWidth={activeTab === id ? 2.5 : 2} />
    </button>
  );

  return (
    <div className="h-screen w-full flex flex-col bg-[#0b0c10] text-slate-200 overflow-hidden font-sans border border-slate-800 shadow-2xl relative">
      {/* Absolute Ambient Glow */}
      <div className="absolute top-0 left-1/4 w-[500px] h-[500px] bg-indigo-500/10 blur-[120px] rounded-full pointer-events-none"></div>
      <div className="absolute bottom-0 right-1/4 w-[400px] h-[400px] bg-purple-500/10 blur-[100px] rounded-full pointer-events-none"></div>

      {/* Draggable Title Bar */}
      <div 
        style={{ WebkitAppRegion: 'drag' }} 
        className="flex justify-between items-center px-5 py-3 border-b border-white/5 bg-black/20 backdrop-blur-md z-50 relative"
      >
        <div className="flex gap-4 items-center" style={{ WebkitAppRegion: 'no-drag' }}>
          <div className="flex gap-2">
             <div className="w-3.5 h-3.5 rounded-full bg-[#ff5f56] hover:bg-red-400 cursor-pointer shadow-sm transition" onClick={closeApp}></div>
             <div className="w-3.5 h-3.5 rounded-full bg-[#ffbd2e] hover:bg-yellow-400 cursor-pointer shadow-sm transition" onClick={minimizeApp}></div>
             <div className="w-3.5 h-3.5 rounded-full bg-[#27c93f] hover:bg-green-400 cursor-pointer shadow-sm transition" onClick={maximizeApp}></div>
          </div>
          <span className="ml-2 text-xs font-semibold tracking-[0.2em] text-indigo-200/70 flex items-center gap-2">
            <Sparkles size={12} className="text-purple-400" />
            AI-ACCESS GEMINI
          </span>
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden z-10 relative">
        {/* Sidebar */}
        <div className="w-20 bg-[#13141c]/80 backdrop-blur-xl flex flex-col items-center py-6 border-r border-white/5 gap-4 shadow-2xl">
          <NavItem id="chat" icon={MessageSquare} label="Chat" />
          <NavItem id="files" icon={FolderSearch} label="File Manager" />
          <NavItem id="code" icon={Code2} label="Code Editor" />
          <NavItem id="media" icon={ImageIcon} label="Media & Music" />
          
          <div className="flex-1"></div>
          
          <NavItem id="settings" icon={Settings} label="Settings" />
        </div>

        {/* Main Content Area */}
        <div className="flex-1 flex flex-col relative bg-gradient-to-b from-transparent to-black/20">
          
          <AnimatePresence mode="wait">
            {activeTab === 'chat' && (
              <motion.div 
                key="chat"
                initial={{ opacity: 0, scale: 0.98 }} 
                animate={{ opacity: 1, scale: 1 }} 
                exit={{ opacity: 0 }}
                transition={{ duration: 0.2 }}
                className="flex flex-col h-full w-full max-w-4xl mx-auto p-6"
              >
                <div className="flex items-center gap-3 mb-6">
                   <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg shadow-indigo-500/30">
                      <Sparkles size={20} className="text-white" />
                   </div>
                   <h2 className="text-xl font-medium text-slate-100 tracking-wide">Hi, I'm ready to help.</h2>
                   <span className="text-xs px-2 py-1 rounded-full bg-white/5 border border-white/10 text-slate-400">Status: {status}</span>
                </div>

                <div 
                  className="flex-1 overflow-y-auto space-y-6 pr-4 custom-scrollbar pb-6"
                  ref={scrollRef}
                >
                  {messages.map((m, i) => (
                    <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                      <div className={`max-w-[75%] p-4 text-[15px] leading-relaxed shadow-sm ${
                        m.role === 'user' 
                          ? 'bg-[#1e1e24] text-slate-100 rounded-3xl rounded-br-sm border border-white/5' 
                          : 'bg-transparent text-slate-300'
                      }`}>
                        {m.role === 'system' ? <div className="text-indigo-400 font-mono text-sm mb-1">SYSTEM</div> : null}
                        {m.role === 'assistant' ? <div className="text-purple-400 flex items-center gap-2 font-medium text-sm mb-2"><Sparkles size={14}/> AI-Access</div> : null}
                        {m.content}
                      </div>
                    </div>
                  ))}
                  {isTyping && (
                    <div className="flex justify-start">
                      <div className="bg-transparent text-slate-400 p-4 rounded-3xl flex gap-2 items-center">
                         <Loader2 size={16} className="animate-spin text-indigo-400" /> Thinking...
                      </div>
                    </div>
                  )}
                </div>

                <div className="relative mt-2 p-1 rounded-3xl bg-gradient-to-tr from-indigo-500/20 to-purple-500/20 backdrop-blur-md border border-white/10">
                  <div className="flex bg-[#13141c] rounded-[22px] overflow-hidden">
                    <input 
                      type="text" 
                      value={input}
                      onChange={e => setInput(e.target.value)}
                      onKeyDown={e => e.key === 'Enter' && handleSend()}
                      placeholder="Ask me anything, mention files, or request code..." 
                      className="w-full bg-transparent px-6 py-4 text-[15px] focus:outline-none text-slate-200 placeholder-slate-500"
                    />
                    <button 
                      onClick={handleSend}
                      disabled={!input.trim() || isTyping}
                      className="px-6 flex items-center justify-center text-indigo-400 hover:text-indigo-300 disabled:opacity-50 disabled:hover:text-indigo-400 transition"
                    >
                      <Send size={20} className={input.trim() ? 'opacity-100' : 'opacity-0'} />
                    </button>
                  </div>
                </div>
              </motion.div>
            )}

            {activeTab === 'files' && (
              <motion.div key="files" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="h-full p-6 w-full max-w-5xl mx-auto">
                 <FileBrowser />
              </motion.div>
            )}

            {activeTab === 'code' && (
              <motion.div key="code" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="h-full p-6 w-full max-w-6xl mx-auto">
                 <CodeWorkspace />
              </motion.div>
            )}

            {activeTab === 'media' && (
              <motion.div key="media" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="h-full p-6 w-full max-w-5xl mx-auto">
                 <MediaStudio />
              </motion.div>
            )}

            {activeTab === 'settings' && (
              <motion.div key="settings" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="h-full p-8 w-full max-w-3xl mx-auto flex flex-col gap-8">
                <div>
                  <h2 className="text-3xl font-light text-slate-100 mb-2">Configuration</h2>
                  <p className="text-slate-400">Manage your system integration and device tokens.</p>
                </div>
                
                <div className="p-6 bg-[#13141c] border border-white/5 rounded-2xl shadow-xl">
                  <h3 className="text-lg font-medium text-indigo-300 mb-2">Device Token Binding</h3>
                  <p className="text-sm text-slate-400 mb-4">Paste the sync token generated from your Config Web Portal. This grants the Desktop Agent secure access to your AI models.</p>
                  <div className="flex gap-3">
                    <input 
                      type="text" 
                      value={token}
                      onChange={e => setToken(e.target.value)}
                      className="bg-[#0b0c10] border border-white/10 rounded-xl px-4 py-3 flex-1 focus:outline-none focus:border-indigo-500/50 transition font-mono text-sm"
                      placeholder="e.g. AI-9F8X7D..."
                    />
                    <button onClick={submitToken} className="bg-indigo-600 hover:bg-indigo-500 transition px-6 py-3 rounded-xl font-medium text-white shadow-lg shadow-indigo-600/20">Bind System</button>
                  </div>
                  <p className="text-xs text-slate-500 mt-3">API keys stay in backend env only. Desktop app uses this token.</p>
                </div>
                
                <div className="p-6 bg-[#13141c] border border-white/5 rounded-2xl shadow-xl">
                  <h3 className="text-lg font-medium text-purple-300 mb-2">Exam Mode / Background Vision</h3>
                  <p className="text-sm text-slate-400 mb-4">Toggle Exam mode from the system tray icon in your Windows Taskbar. Once enabled, press <strong>SHIFT</strong> at any time to instantly parse on-screen content and display the hidden answer overlay.</p>
                  <div className="flex gap-2">
                     <span className="px-3 py-1 bg-green-500/20 text-green-400 text-xs rounded-full font-medium border border-green-500/30">Overlay Active</span>
                     <span className="px-3 py-1 bg-indigo-500/20 text-indigo-400 text-xs rounded-full font-medium border border-indigo-500/30">Shift Hook Ready</span>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    
      {/* Global strict resets for UI aesthetics */}
      <style>{`
        input, button { font-family: inherit; }
        .custom-scrollbar::-webkit-scrollbar { width: 6px; }
        .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
        .custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 10px; }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.2); }
      `}</style>
    </div>
  );
}
