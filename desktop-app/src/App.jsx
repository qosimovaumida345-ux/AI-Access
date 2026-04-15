import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Sparkles, 
  MessageSquare, 
  FolderSearch, 
  Code2, 
  Image as ImageIcon, 
  Settings, 
  Send,
  Loader2,
  ShieldAlert,
  Terminal,
  Cpu,
  Zap
} from 'lucide-react';
import FileBrowser from './FileBrowser';
import CodeWorkspace from './CodeWorkspace';
import MediaStudio from './MediaStudio';
import { chatWithAI } from './services/api';

export default function App() {
  const [activeTab, setActiveTab] = useState('chat');
  const [token, setToken] = useState('NOT_BOUND');
  const [isSudo, setIsSudo] = useState(false);
  const [messages, setMessages] = useState([{ role: 'system', content: 'ShadowForge OS Online. Universal AI-Access established.' }]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [status, setStatus] = useState('Standby');
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
    setStatus('Processing...');

    try {
      const res = await chatWithAI(chatHistory.filter(m => m.role !== 'system'), {
        token,
        sudo: isSudo
      });
      setMessages([...chatHistory, { role: 'assistant', content: res.text }]);
      setStatus(`${res.provider ? res.provider.toUpperCase() : 'AI'} ACTIVE`);
    } catch (e) {
      setMessages([...chatHistory, { role: 'assistant', content: "CRITICAL: Connection to AI Brain lost. Ensure the Python Core is running." }]);
      setStatus('OFFLINE');
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
      className={`group relative flex items-center justify-center w-12 h-12 rounded-xl transition-all duration-300 ${
        activeTab === id 
          ? 'bg-purple-600/20 text-purple-400 shadow-[0_0_20px_rgba(102,0,204,0.3)]' 
          : 'text-gray-500 hover:text-gray-200'
      }`}
      title={label}
    >
      <Icon size={22} strokeWidth={activeTab === id ? 2.5 : 2} />
      {activeTab === id && (
        <motion.div layoutId="nav-indicator" className="absolute -left-1 w-1 h-6 bg-purple-500 rounded-full" />
      )}
    </button>
  );

  return (
    <div className="h-screen w-full flex flex-col bg-bg-deep text-text-primary overflow-hidden relative">
      {/* Background Orbs */}
      <div className="absolute top-[-10%] left-[10%] w-[40%] h-[40%] bg-purple-900/10 blur-[150px] rounded-full"></div>
      <div className="absolute bottom-[-10%] right-[10%] w-[40%] h-[40%] bg-red-900/5 blur-[150px] rounded-full"></div>

      {/* Control Bar */}
      <div 
        style={{ WebkitAppRegion: 'drag' }} 
        className="flex justify-between items-center px-6 py-4 z-50 glass border-b-0"
      >
        <div className="flex gap-4 items-center" style={{ WebkitAppRegion: 'no-drag' }}>
          <div className="flex gap-2">
             <div className="w-3 h-3 rounded-full bg-red-500/80 hover:bg-red-500 transition cursor-pointer" onClick={closeApp}></div>
             <div className="w-3 h-3 rounded-full bg-yellow-500/80 hover:bg-yellow-500 transition cursor-pointer" onClick={minimizeApp}></div>
             <div className="w-3 h-3 rounded-full bg-green-500/80 hover:bg-green-500 transition cursor-pointer" onClick={maximizeApp}></div>
          </div>
          <div className="h-4 w-px bg-white/10 mx-2"></div>
          <span className="text-[10px] font-bold tracking-[.3em] uppercase text-text-muted flex items-center gap-2">
            <Zap size={10} className="text-purple-500 animate-pulse" />
            ShadowForge OS
          </span>
        </div>

        <div className="flex items-center gap-4" style={{ WebkitAppRegion: 'no-drag' }}>
          <div className={`flex items-center gap-2 px-3 py-1 rounded-full text-[10px] font-bold border transition-all ${
            isSudo ? 'bg-red-500/10 border-red-500/30 text-red-400' : 'bg-white/5 border-white/10 text-text-muted'
          }`}>
            <ShieldAlert size={12} />
            {isSudo ? 'SUDO ACTIVE' : 'USER MODE'}
            <button 
              onClick={() => setIsSudo(!isSudo)}
              className={`ml-2 w-8 h-4 rounded-full relative transition-colors ${isSudo ? 'bg-red-500' : 'bg-gray-700'}`}
            >
              <div className={`absolute top-0.5 w-3 h-3 bg-white rounded-full transition-all ${isSudo ? 'left-4.5' : 'left-0.5'}`}></div>
            </button>
          </div>
          <div className="flex items-center gap-2 text-[10px] text-text-muted">
             <Cpu size={12} />
             {status}
          </div>
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden z-10">
        {/* Sidebar */}
        <div className="w-20 glass border-l-0 border-y-0 flex flex-col items-center py-8 gap-6">
          <NavItem id="chat" icon={MessageSquare} label="Neural Chat" />
          <NavItem id="files" icon={FolderSearch} label="FS Explorer" />
          <NavItem id="code" icon={Code2} label="Logic Forge" />
          <NavItem id="media" icon={ImageIcon} label="Asset Studio" />
          <div className="flex-1"></div>
          <NavItem id="settings" icon={Settings} label="Core Config" />
        </div>

        {/* Main Workspace */}
        <div className="flex-1 flex flex-col relative">
          <AnimatePresence mode="wait">
            {activeTab === 'chat' && (
              <motion.div 
                key="chat"
                initial={{ opacity: 0, y: 10 }} 
                animate={{ opacity: 1, y: 0 }} 
                exit={{ opacity: 0, y: -10 }}
                className="flex flex-col h-full w-full max-w-5xl mx-auto p-8"
              >
                <div className="flex-1 overflow-y-auto space-y-8 pr-4 custom-scrollbar">
                  {messages.map((m, i) => (
                    <motion.div 
                      initial={{ opacity: 0, x: m.role === 'user' ? 20 : -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      key={i} 
                      className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}
                    >
                      <div className={`max-w-[85%] ${
                        m.role === 'user' 
                          ? 'glass-card border-purple-500/20 rounded-tr-none' 
                          : 'bg-transparent border-none p-0'
                      }`}>
                        {m.role === 'system' && (
                          <div className="flex items-center gap-2 text-purple-400 font-mono text-xs mb-2">
                             <Terminal size={12} /> SYSTEM_KERNEL_INIT
                          </div>
                        )}
                        {m.role === 'assistant' && (
                          <div className="flex items-center gap-2 text-purple-400 font-bold text-xs mb-3 tracking-widest">
                             <Sparkles size={14} className="animate-pulse" /> SHADOW_FORGE
                          </div>
                        )}
                        <div className={`text-[15px] leading-relaxed ${m.role === 'assistant' ? 'text-text-primary' : 'text-gray-200'}`}>
                           {m.content.split('\n').map((line, lid) => (
                             <p key={lid} className="mb-2">{line}</p>
                           ))}
                        </div>
                      </div>
                    </motion.div>
                  ))}
                  {isTyping && (
                    <div className="flex justify-start">
                       <div className="flex gap-2 items-center text-xs text-text-muted font-mono">
                          <Loader2 size={14} className="animate-spin" /> THINKING...
                       </div>
                    </div>
                  )}
                  <div ref={scrollRef} />
                </div>

                {/* Input Section */}
                <div className="mt-8 relative">
                   <div className="glass rounded-2xl p-2 flex items-center shadow-2xl">
                      <input 
                        type="text" 
                        value={input}
                        onChange={e => setInput(e.target.value)}
                        onKeyDown={e => e.key === 'Enter' && handleSend()}
                        placeholder={isSudo ? "Sudo mode active. Use full system access..." : "Ask anything..."} 
                        className="flex-1 bg-transparent px-6 py-4 text-sm focus:outline-none placeholder-gray-600"
                      />
                      <button 
                        onClick={handleSend}
                        disabled={!input.trim() || isTyping}
                        className={`p-4 rounded-xl transition-all ${
                          input.trim() 
                            ? 'bg-purple-600 text-white shadow-lg shadow-purple-600/30' 
                            : 'bg-white/5 text-gray-600'
                        }`}
                      >
                        <Send size={18} />
                      </button>
                   </div>
                </div>
              </motion.div>
            )}

            {activeTab === 'files' && (
              <motion.div key="files" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="h-full p-6"><FileBrowser /></motion.div>
            )}
            {activeTab === 'code' && (
              <motion.div key="code" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="h-full p-6"><CodeWorkspace /></motion.div>
            )}
            {activeTab === 'media' && (
              <motion.div key="media" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="h-full p-6"><MediaStudio /></motion.div>
            )}
            
            {activeTab === 'settings' && (
              <motion.div key="settings" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="h-full p-12 max-w-3xl mx-auto space-y-12">
                 <div className="space-y-2">
                    <h2 className="text-4xl font-light tracking-tight">Core Settings</h2>
                    <p className="text-text-muted">Configure your ShadowForge instance.</p>
                 </div>
                 
                 <div className="glass-card space-y-6">
                    <h3 className="text-purple-400 font-bold text-xs tracking-widest uppercase">System Sync</h3>
                    <div className="flex gap-4">
                       <input 
                         type="text" 
                         value={token}
                         onChange={e => setToken(e.target.value)}
                         className="flex-1 bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-xs font-mono"
                         placeholder="SYNC_TOKEN"
                       />
                       <button onClick={submitToken} className="bg-purple-600 px-6 py-3 rounded-xl text-xs font-bold hover:bg-purple-500 transition">SYCHRONIZE</button>
                    </div>
                 </div>

                 <div className="glass-card bg-red-500/5 border-red-500/20">
                    <h3 className="text-red-400 font-bold text-xs tracking-widest uppercase mb-4">Danger Zone</h3>
                    <p className="text-xs text-text-muted mb-4">Sudo mode allows the AI to execute system commands, modify settings, and access sensitive files. Use with caution.</p>
                    <div className="flex items-center justify-between">
                       <span className="text-xs font-bold">Unrestricted Access</span>
                       <button 
                        onClick={() => setIsSudo(!isSudo)}
                        className={`px-4 py-2 rounded-lg text-[10px] font-bold border transition-all ${
                          isSudo ? 'bg-red-600 border-red-500' : 'bg-transparent border-white/10'
                        }`}
                       >
                         {isSudo ? 'DEACTIVATE SUDO' : 'ACTIVATE SUDO'}
                       </button>
                    </div>
                 </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
