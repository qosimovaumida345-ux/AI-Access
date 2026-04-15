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
  Zap,
  Globe,
  Key,
  Server
} from 'lucide-react';
import FileBrowser from './FileBrowser';
import CodeWorkspace from './CodeWorkspace';
import MediaStudio from './MediaStudio';
import { chatWithAI, checkHealth } from './services/api';

export default function App() {
  const [activeTab, setActiveTab] = useState('chat');
  const [token, setToken] = useState('NOT_BOUND');
  const [isSudo, setIsSudo] = useState(false);
  const [messages, setMessages] = useState([{ role: 'system', content: 'ShadowForge OS Online. Universal AI-Access established.' }]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [status, setStatus] = useState('Standby');
  const [isBooting, setIsBooting] = useState(true);
  const [bootMessage, setBootMessage] = useState('Initializing ShadowForge Kernal...');
  const [backendUrl, setBackendUrl] = useState(localStorage.getItem('SHADOWFORGE_BACKEND_URL') || '');
  const [apiKeys, setApiKeys] = useState(JSON.parse(localStorage.getItem('SHADOWFORGE_API_KEYS') || '{}'));
  
  const scrollRef = useRef(null);

  useEffect(() => {
    const initializeSystem = async () => {
      const messages = [
        'Verifying ShadowForge Kernal...',
        'Establishing Secure Neural Link...',
        'Awakening AI Brain (Render Wake-up)...',
        'Syncing Global Neural Sync...',
        'Finalizing Logic Gates...'
      ];
      
      let msgIndex = 0;
      const interval = setInterval(() => {
        setBootMessage(messages[msgIndex % messages.length]);
        msgIndex++;
      }, 3000);

      const wakeupServer = async () => {
        try {
          await checkHealth();
          clearInterval(interval);
          setIsBooting(false);
          setStatus('ONLINE');
        } catch (e) {
          setTimeout(wakeupServer, 5000);
        }
      };

      wakeupServer();
    };

    initializeSystem();
  }, []);

  useEffect(() => {
    localStorage.setItem('SHADOWFORGE_BACKEND_URL', backendUrl);
  }, [backendUrl]);

  useEffect(() => {
    localStorage.setItem('SHADOWFORGE_API_KEYS', JSON.stringify(apiKeys));
  }, [apiKeys]);

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
        sudo: isSudo,
        api_keys: apiKeys
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
              <motion.div 
                key="settings" 
                initial={{ opacity: 0, x: 20 }} 
                animate={{ opacity: 1, x: 0 }} 
                exit={{ opacity: 0, x: -20 }}
                className="h-full p-12 max-w-3xl mx-auto space-y-12 overflow-y-auto custom-scrollbar"
              >
                  <div className="space-y-2">
                    <h2 className="text-4xl font-light tracking-tight">Core Config</h2>
                    <p className="text-text-muted">Configure your global ShadowForge instance.</p>
                  </div>

                  <div className="glass-card space-y-6">
                    <div className="flex items-center gap-2 mb-2">
                       <Globe size={14} className="text-purple-400" />
                       <h3 className="text-purple-400 font-bold text-xs tracking-widest uppercase">Global Backend</h3>
                    </div>
                    <div className="space-y-4">
                       <div className="space-y-2">
                          <label className="text-[10px] text-text-muted uppercase tracking-widest">Render/Custom Backend URL</label>
                          <input 
                            type="text" 
                            value={backendUrl}
                            onChange={e => setBackendUrl(e.target.value)}
                            className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-xs font-mono"
                            placeholder="https://your-app.onrender.com"
                          />
                       </div>
                    </div>
                  </div>

                  <div className="glass-card space-y-6">
                    <div className="flex items-center gap-2 mb-2">
                       <Key size={14} className="text-purple-400" />
                       <h3 className="text-purple-400 font-bold text-xs tracking-widest uppercase">Neural Credentials</h3>
                    </div>
                    <div className="space-y-4">
                       <div className="space-y-2">
                          <label className="text-[10px] text-text-muted uppercase tracking-widest">Groq API Key</label>
                          <input 
                            type="password" 
                            value={apiKeys.GROQ_API_KEY || ''}
                            onChange={e => setApiKeys({...apiKeys, GROQ_API_KEY: e.target.value})}
                            className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-xs font-mono"
                            placeholder="gsk_..."
                          />
                       </div>
                       <div className="space-y-2">
                          <label className="text-[10px] text-text-muted uppercase tracking-widest">Google AI (Gemini) Key</label>
                          <input 
                            type="password" 
                            value={apiKeys.GOOGLE_AI_API_KEY || ''}
                            onChange={e => setApiKeys({...apiKeys, GOOGLE_AI_API_KEY: e.target.value})}
                            className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-xs font-mono"
                            placeholder="AIza..."
                          />
                       </div>
                    </div>
                  </div>

                  <div className="glass-card bg-red-500/5 border-red-500/20">
                    <h3 className="text-red-400 font-bold text-xs tracking-widest uppercase mb-4">Danger Zone</h3>
                    <p className="text-xs text-text-muted mb-4">Sudo mode allows the AI to execute system commands. Use with caution.</p>
                    <div className="flex items-center justify-between">
                       <span className="text-xs font-bold">Unrestricted Access</span>
                       <button 
                         onClick={() => setIsSudo(!isSudo)}
                         className={`px-4 py-2 rounded-lg text-[10px] font-bold border transition-all ${
                           isSudo ? 'bg-red-600 border-red-500 text-white' : 'bg-transparent border-white/10 text-gray-400'
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
      <AnimatePresence>
        {isBooting && (
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[100] bg-bg-deep flex flex-col items-center justify-center p-8 text-center"
          >
            <div className="absolute top-[-10%] left-[10%] w-[40%] h-[40%] bg-purple-900/20 blur-[150px] rounded-full animate-pulse"></div>
            
            <div className="relative">
               <motion.div 
                 animate={{ rotate: 360 }}
                 transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
                 className="w-32 h-32 rounded-full border-t-2 border-l-2 border-purple-500/30"
               />
               <motion.div 
                 animate={{ rotate: -360 }}
                 transition={{ duration: 15, repeat: Infinity, ease: "linear" }}
                 className="absolute inset-2 rounded-full border-b-2 border-r-2 border-purple-400/50 shadow-[0_0_30px_rgba(168,85,247,0.2)]"
               />
               <div className="absolute inset-0 flex items-center justify-center">
                  <Zap size={32} className="text-purple-500 animate-pulse" />
               </div>
            </div>

            <div className="mt-12 space-y-4">
               <h1 className="text-xl font-bold tracking-[0.5em] uppercase text-white">ShadowForge</h1>
               <div className="h-px w-24 bg-white/10 mx-auto"></div>
               <p className="text-xs font-mono text-purple-400/80 animate-pulse">{bootMessage}</p>
            </div>

            <div className="absolute bottom-12 left-0 right-0">
               <div className="max-w-xs mx-auto space-y-2">
                  <div className="flex justify-between text-[10px] text-text-muted px-1 uppercase tracking-widest">
                     <span>Awakening Kernal</span>
                     <span>AUTO</span>
                  </div>
                  <div className="h-1 w-full bg-white/5 rounded-full overflow-hidden">
                     <motion.div 
                       animate={{ width: ['20%', '80%', '60%'] }}
                       transition={{ duration: 10, repeat: Infinity }}
                       className="h-full bg-purple-600 shadow-[0_0_10px_rgba(168,85,247,0.5)]"
                     />
                  </div>
               </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
