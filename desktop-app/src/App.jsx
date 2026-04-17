import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
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
  Server,
  ChevronRight,
  Activity,
  Minus,
  Square,
  X,
  Bot,
  User
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
  const [bootMessage, setBootMessage] = useState('Initializing ShadowForge Kernel...');
  const [bootStep, setBootStep] = useState(0);
  const [backendUrl, setBackendUrl] = useState(localStorage.getItem('SHADOWFORGE_BACKEND_URL') || '');
  const [apiKeys, setApiKeys] = useState(JSON.parse(localStorage.getItem('SHADOWFORGE_API_KEYS') || '{}'));
  
  const scrollRef = useRef(null);
  const inputRef = useRef(null);

  const bootSequence = [
    'Initializing ShadowForge Kernel...',
    'Establishing Secure Neural Link...',
    'Awakening AI Brain (Render Wake-up)...',
    'Syncing Global Neural Network...',
    'Finalizing Logic Gates...'
  ];

  useEffect(() => {
    const initializeSystem = async () => {
      let msgIndex = 0;
      const interval = setInterval(() => {
        msgIndex = (msgIndex + 1) % bootSequence.length;
        setBootMessage(bootSequence[msgIndex]);
        setBootStep(msgIndex);
      }, 3000);

      const wakeupServer = async () => {
        try {
          await checkHealth();
          clearInterval(interval);
          setBootStep(bootSequence.length);
          setTimeout(() => { setIsBooting(false); setStatus('ONLINE'); }, 600);
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

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isTyping]);

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
      setMessages([...chatHistory, { role: 'assistant', content: 'CRITICAL: Connection to AI Brain lost. Ensure the Python Core is running.' }]);
      setStatus('OFFLINE');
    } finally {
      setIsTyping(false);
    }
  };

  const closeApp    = () => window.electronAPI && window.electronAPI.hideWindow();
  const minimizeApp = () => window.electronAPI && window.electronAPI.minimizeWindow();
  const maximizeApp = () => window.electronAPI && window.electronAPI.maximizeWindow();
  const submitToken = () => window.electronAPI && window.electronAPI.setToken(token);

  const isOnline = status === 'ONLINE' || status.includes('ACTIVE');
  const isOffline = status === 'OFFLINE';

  // ── NAV ITEM ──────────────────────────────────────────────────
  const NavItem = ({ id, icon: Icon, label }) => (
    <button
      onClick={() => setActiveTab(id)}
      title={label}
      style={{
        position: 'relative',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        width: '44px',
        height: '44px',
        borderRadius: '12px',
        border: 'none',
        cursor: 'pointer',
        transition: 'all 0.2s cubic-bezier(0.22, 1, 0.36, 1)',
        background: activeTab === id
          ? 'rgba(109, 40, 217, 0.18)'
          : 'transparent',
        color: activeTab === id ? 'var(--violet-400)' : 'var(--text-muted)',
      }}
      onMouseEnter={e => {
        if (activeTab !== id) {
          e.currentTarget.style.background = 'rgba(139,92,246,0.08)';
          e.currentTarget.style.color = 'var(--text-secondary)';
        }
      }}
      onMouseLeave={e => {
        if (activeTab !== id) {
          e.currentTarget.style.background = 'transparent';
          e.currentTarget.style.color = 'var(--text-muted)';
        }
      }}
    >
      <Icon size={19} strokeWidth={activeTab === id ? 2 : 1.5} />
      {activeTab === id && (
        <motion.div
          layoutId="nav-pill"
          style={{
            position: 'absolute',
            left: '-1px',
            width: '2px',
            height: '22px',
            borderRadius: '0 2px 2px 0',
            background: 'linear-gradient(to bottom, var(--cyan-400), var(--violet-500))',
          }}
        />
      )}
    </button>
  );

  // ── CHAT MESSAGE ──────────────────────────────────────────────
  const ChatMessage = ({ m, i }) => {
    if (m.role === 'system') return (
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: i * 0.04 }}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          padding: '8px 14px',
          borderRadius: '8px',
          background: 'rgba(109, 40, 217, 0.06)',
          border: '1px solid rgba(109, 40, 217, 0.12)',
          width: 'fit-content',
          maxWidth: '90%',
          margin: '0 auto',
        }}
      >
        <Terminal size={11} color="var(--violet-400)" />
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--violet-300)', letterSpacing: '0.05em' }}>
          {m.content}
        </span>
      </motion.div>
    );

    const isUser = m.role === 'user';
    return (
      <motion.div
        initial={{ opacity: 0, x: isUser ? 16 : -16 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ delay: i * 0.03, ease: [0.22, 1, 0.36, 1] }}
        style={{ display: 'flex', justifyContent: isUser ? 'flex-end' : 'flex-start', gap: '10px', alignItems: 'flex-start' }}
      >
        {!isUser && (
          <div style={{
            flexShrink: 0,
            width: '28px', height: '28px',
            borderRadius: '8px',
            background: 'rgba(109,40,217,0.15)',
            border: '1px solid rgba(109,40,217,0.25)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            marginTop: '2px',
          }}>
            <Bot size={13} color="var(--violet-400)" />
          </div>
        )}
        <div style={{
          maxWidth: '82%',
          padding: isUser ? '12px 16px' : '12px 0',
          borderRadius: isUser ? '16px 4px 16px 16px' : '0',
          background: isUser ? 'rgba(109,40,217,0.14)' : 'transparent',
          border: isUser ? '1px solid rgba(109,40,217,0.2)' : 'none',
        }}>
          {!isUser && (
            <div style={{
              display: 'flex', alignItems: 'center', gap: '6px',
              marginBottom: '8px',
              fontFamily: 'var(--font-mono)',
              fontSize: '10px',
              color: 'var(--cyan-400)',
              letterSpacing: '0.12em',
              textTransform: 'uppercase',
            }}>
              <Zap size={10} />
              ShadowForge
            </div>
          )}
          <div style={{
            fontSize: '14px',
            lineHeight: '1.7',
            color: isUser ? 'var(--text-primary)' : 'var(--text-secondary)',
            fontFamily: 'var(--font-body)',
          }}>
            {m.content.split('\n').map((line, lid) => (
              <p key={lid} style={{ marginBottom: line ? '6px' : 0 }}>{line}</p>
            ))}
          </div>
        </div>
        {isUser && (
          <div style={{
            flexShrink: 0,
            width: '28px', height: '28px',
            borderRadius: '8px',
            background: 'rgba(34,211,238,0.1)',
            border: '1px solid rgba(34,211,238,0.2)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            marginTop: '2px',
          }}>
            <User size={13} color="var(--cyan-300)" />
          </div>
        )}
      </motion.div>
    );
  };

  // ── SETTINGS FIELD ────────────────────────────────────────────
  const SettingsInput = ({ label, type = 'text', value, onChange, placeholder }) => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
      <label style={{
        fontFamily: 'var(--font-mono)',
        fontSize: '10px',
        color: 'var(--text-muted)',
        textTransform: 'uppercase',
        letterSpacing: '0.1em',
      }}>{label}</label>
      <input
        type={type}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        style={{
          width: '100%',
          background: 'rgba(0,0,0,0.35)',
          border: '1px solid var(--border-default)',
          borderRadius: '10px',
          padding: '11px 14px',
          fontSize: '12px',
          fontFamily: 'var(--font-mono)',
          color: 'var(--text-primary)',
          transition: 'border-color 0.2s',
          outline: 'none',
        }}
        onFocus={e => e.target.style.borderColor = 'var(--violet-500)'}
        onBlur={e => e.target.style.borderColor = 'var(--border-default)'}
      />
    </div>
  );

  // ── MAIN RENDER ───────────────────────────────────────────────
  return (
    <div style={{
      height: '100vh',
      width: '100%',
      display: 'flex',
      flexDirection: 'column',
      background: 'var(--bg-void)',
      color: 'var(--text-primary)',
      overflow: 'hidden',
      position: 'relative',
      fontFamily: 'var(--font-body)',
    }}>
      {/* Ambient background glows */}
      <div style={{
        position: 'absolute', top: '-15%', left: '5%',
        width: '45%', height: '50%',
        background: 'radial-gradient(ellipse, rgba(109,40,217,0.07) 0%, transparent 70%)',
        pointerEvents: 'none',
      }} />
      <div style={{
        position: 'absolute', bottom: '-10%', right: '0%',
        width: '40%', height: '45%',
        background: 'radial-gradient(ellipse, rgba(8,145,178,0.05) 0%, transparent 70%)',
        pointerEvents: 'none',
      }} />

      {/* ── TITLE BAR ─────────────────────────────────────────── */}
      <div
        style={{
          WebkitAppRegion: 'drag',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '0 20px',
          height: '44px',
          background: 'rgba(7, 3, 18, 0.85)',
          backdropFilter: 'blur(20px)',
          borderBottom: '1px solid var(--border-subtle)',
          position: 'relative',
          zIndex: 50,
          flexShrink: 0,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px', WebkitAppRegion: 'no-drag' }}>
          {/* macOS traffic lights */}
          <div style={{ display: 'flex', gap: '7px', alignItems: 'center' }}>
            {[
              { color: '#ff5f57', hover: '#ff3b30', action: closeApp },
              { color: '#febc2e', hover: '#ffbd2e', action: minimizeApp },
              { color: '#28c840', hover: '#24b237', action: maximizeApp },
            ].map(({ color, hover, action }, i) => (
              <button
                key={i}
                onClick={action}
                style={{
                  width: '12px', height: '12px',
                  borderRadius: '50%',
                  background: color,
                  border: 'none',
                  cursor: 'pointer',
                  transition: 'opacity 0.15s',
                  opacity: 0.85,
                }}
                onMouseEnter={e => e.currentTarget.style.opacity = '1'}
                onMouseLeave={e => e.currentTarget.style.opacity = '0.85'}
              />
            ))}
          </div>
          <div style={{ width: '1px', height: '16px', background: 'var(--border-subtle)' }} />
          <div style={{
            display: 'flex', alignItems: 'center', gap: '6px',
            fontFamily: 'var(--font-mono)',
            fontSize: '10px',
            color: 'var(--text-muted)',
            letterSpacing: '0.25em',
            textTransform: 'uppercase',
          }}>
            <Zap size={9} color="var(--violet-400)" style={{ flexShrink: 0 }} />
            ShadowForge OS
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', WebkitAppRegion: 'no-drag' }}>
          {/* Sudo toggle */}
          <button
            onClick={() => setIsSudo(!isSudo)}
            style={{
              display: 'flex', alignItems: 'center', gap: '7px',
              padding: '4px 10px',
              borderRadius: '20px',
              border: `1px solid ${isSudo ? 'rgba(220,38,38,0.35)' : 'var(--border-subtle)'}`,
              background: isSudo ? 'rgba(220,38,38,0.08)' : 'transparent',
              cursor: 'pointer',
              transition: 'all 0.2s',
              fontFamily: 'var(--font-mono)',
              fontSize: '10px',
              color: isSudo ? 'var(--red-400)' : 'var(--text-muted)',
              letterSpacing: '0.1em',
            }}
          >
            <ShieldAlert size={10} />
            {isSudo ? 'SUDO' : 'USER'}
            <div style={{
              width: '24px', height: '12px',
              borderRadius: '6px',
              background: isSudo ? 'var(--red-600)' : 'rgba(255,255,255,0.08)',
              position: 'relative',
              transition: 'background 0.2s',
            }}>
              <div style={{
                position: 'absolute',
                top: '2px', left: isSudo ? '14px' : '2px',
                width: '8px', height: '8px',
                borderRadius: '50%',
                background: '#fff',
                transition: 'left 0.2s',
              }} />
            </div>
          </button>

          {/* Status */}
          <div style={{
            display: 'flex', alignItems: 'center', gap: '6px',
            fontFamily: 'var(--font-mono)',
            fontSize: '10px',
            color: isOnline ? 'var(--green-500)' : isOffline ? 'var(--red-400)' : 'var(--amber-400)',
            letterSpacing: '0.1em',
          }}>
            <span className={`status-dot ${isOnline ? 'online' : isOffline ? 'offline' : 'loading'}`} />
            {status}
          </div>
        </div>
      </div>

      {/* ── BODY ──────────────────────────────────────────────── */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden', position: 'relative', zIndex: 10 }}>

        {/* ── SIDEBAR ─────────────────────────────────────────── */}
        <div style={{
          width: '64px',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          padding: '20px 0',
          gap: '6px',
          background: 'rgba(7, 3, 18, 0.6)',
          backdropFilter: 'blur(20px)',
          borderRight: '1px solid var(--border-subtle)',
          flexShrink: 0,
        }}>
          <NavItem id="chat"     icon={MessageSquare} label="Neural Chat" />
          <NavItem id="files"    icon={FolderSearch}  label="File Explorer" />
          <NavItem id="code"     icon={Code2}         label="Code Forge" />
          <NavItem id="media"    icon={ImageIcon}     label="Asset Studio" />
          <div style={{ flex: 1 }} />
          <NavItem id="settings" icon={Settings}      label="Configuration" />
        </div>

        {/* ── WORKSPACE ───────────────────────────────────────── */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', position: 'relative' }}>
          <AnimatePresence mode="wait">

            {/* CHAT TAB */}
            {activeTab === 'chat' && (
              <motion.div
                key="chat"
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
                style={{ display: 'flex', flexDirection: 'column', height: '100%', maxWidth: '860px', width: '100%', margin: '0 auto', padding: '32px 32px 24px' }}
              >
                <div
                  className="custom-scrollbar"
                  style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '24px', paddingRight: '8px' }}
                >
                  {messages.map((m, i) => <ChatMessage key={i} m={m} i={i} />)}
                  {isTyping && (
                    <motion.div
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      style={{ display: 'flex', alignItems: 'center', gap: '10px' }}
                    >
                      <div style={{
                        width: '28px', height: '28px', borderRadius: '8px',
                        background: 'rgba(109,40,217,0.15)', border: '1px solid rgba(109,40,217,0.25)',
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                      }}>
                        <Bot size={13} color="var(--violet-400)" />
                      </div>
                      <div style={{ display: 'flex', gap: '5px', alignItems: 'center' }}>
                        {[0, 0.2, 0.4].map(delay => (
                          <motion.span
                            key={delay}
                            animate={{ y: [0, -5, 0] }}
                            transition={{ duration: 0.8, repeat: Infinity, delay, ease: 'easeInOut' }}
                            style={{ width: '5px', height: '5px', borderRadius: '50%', background: 'var(--violet-400)', display: 'block' }}
                          />
                        ))}
                      </div>
                    </motion.div>
                  )}
                  <div ref={scrollRef} />
                </div>

                {/* Input */}
                <div style={{ marginTop: '24px' }}>
                  <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    background: 'var(--bg-surface-2)',
                    backdropFilter: 'var(--blur-glass)',
                    border: '1px solid var(--border-default)',
                    borderRadius: '16px',
                    padding: '6px 6px 6px 20px',
                    transition: 'border-color 0.2s',
                    boxShadow: '0 4px 24px rgba(0,0,0,0.4)',
                  }}
                  onFocusCapture={e => e.currentTarget.style.borderColor = 'var(--border-strong)'}
                  onBlurCapture={e => e.currentTarget.style.borderColor = 'var(--border-default)'}
                  >
                    <input
                      ref={inputRef}
                      type="text"
                      value={input}
                      onChange={e => setInput(e.target.value)}
                      onKeyDown={e => e.key === 'Enter' && !e.shiftKey && handleSend()}
                      placeholder={isSudo ? 'Sudo mode active — full system access...' : 'Ask anything...'}
                      style={{
                        flex: 1,
                        background: 'transparent',
                        border: 'none',
                        outline: 'none',
                        fontSize: '14px',
                        color: 'var(--text-primary)',
                        fontFamily: 'var(--font-body)',
                        padding: '10px 0',
                      }}
                    />
                    <button
                      onClick={handleSend}
                      disabled={!input.trim() || isTyping}
                      style={{
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        width: '40px', height: '40px',
                        borderRadius: '11px',
                        border: 'none',
                        cursor: input.trim() && !isTyping ? 'pointer' : 'default',
                        background: input.trim() && !isTyping
                          ? 'linear-gradient(135deg, var(--violet-700), var(--violet-500))'
                          : 'rgba(255,255,255,0.05)',
                        color: input.trim() && !isTyping ? '#fff' : 'var(--text-ghost)',
                        transition: 'all 0.2s',
                        boxShadow: input.trim() && !isTyping ? '0 4px 16px rgba(109,40,217,0.35)' : 'none',
                      }}
                    >
                      {isTyping ? <Loader2 size={16} style={{ animation: 'spin-slow 1s linear infinite' }} /> : <Send size={16} />}
                    </button>
                  </div>
                  <p style={{
                    textAlign: 'center', marginTop: '8px',
                    fontFamily: 'var(--font-mono)', fontSize: '10px',
                    color: 'var(--text-ghost)',
                    letterSpacing: '0.05em',
                  }}>
                    Enter to send · Shift+Enter for new line
                  </p>
                </div>
              </motion.div>
            )}

            {/* FILES TAB */}
            {activeTab === 'files' && (
              <motion.div key="files" initial={{ opacity: 0 }} animate={{ opacity: 1 }} style={{ height: '100%', padding: '24px' }}>
                <FileBrowser />
              </motion.div>
            )}

            {/* CODE TAB */}
            {activeTab === 'code' && (
              <motion.div key="code" initial={{ opacity: 0 }} animate={{ opacity: 1 }} style={{ height: '100%', padding: '24px' }}>
                <CodeWorkspace />
              </motion.div>
            )}

            {/* MEDIA TAB */}
            {activeTab === 'media' && (
              <motion.div key="media" initial={{ opacity: 0 }} animate={{ opacity: 1 }} style={{ height: '100%', padding: '24px' }}>
                <MediaStudio />
              </motion.div>
            )}

            {/* SETTINGS TAB */}
            {activeTab === 'settings' && (
              <motion.div
                key="settings"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
                className="custom-scrollbar"
                style={{ height: '100%', padding: '40px 48px', maxWidth: '720px', margin: '0 auto', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '32px', width: '100%' }}
              >
                <div>
                  <h2 style={{ fontFamily: 'var(--font-display)', fontSize: '28px', fontWeight: 700, letterSpacing: '-0.02em', color: 'var(--text-primary)' }}>
                    Configuration
                  </h2>
                  <p style={{ marginTop: '6px', color: 'var(--text-muted)', fontSize: '14px' }}>
                    Manage your ShadowForge instance settings and credentials.
                  </p>
                </div>

                {/* Backend */}
                <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', paddingBottom: '16px', borderBottom: '1px solid var(--border-subtle)' }}>
                    <Globe size={13} color="var(--cyan-400)" />
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--cyan-400)', textTransform: 'uppercase', letterSpacing: '0.15em' }}>
                      Network Endpoint
                    </span>
                  </div>
                  <SettingsInput
                    label="Render / Custom Backend URL"
                    value={backendUrl}
                    onChange={e => setBackendUrl(e.target.value)}
                    placeholder="https://your-app.onrender.com"
                  />
                </div>

                {/* API Keys */}
                <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', paddingBottom: '16px', borderBottom: '1px solid var(--border-subtle)' }}>
                    <Key size={13} color="var(--violet-400)" />
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--violet-400)', textTransform: 'uppercase', letterSpacing: '0.15em' }}>
                      Neural Credentials
                    </span>
                  </div>
                  <SettingsInput
                    label="Groq API Key"
                    type="password"
                    value={apiKeys.GROQ_API_KEY || ''}
                    onChange={e => setApiKeys({ ...apiKeys, GROQ_API_KEY: e.target.value })}
                    placeholder="gsk_..."
                  />
                  <SettingsInput
                    label="Google AI (Gemini) Key"
                    type="password"
                    value={apiKeys.GOOGLE_AI_API_KEY || ''}
                    onChange={e => setApiKeys({ ...apiKeys, GOOGLE_AI_API_KEY: e.target.value })}
                    placeholder="AIza..."
                  />
                </div>

                {/* Danger Zone */}
                <div className="glass-card" style={{ background: 'rgba(220,38,38,0.04)', borderColor: 'rgba(220,38,38,0.18)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
                    <ShieldAlert size={13} color="var(--red-400)" />
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--red-400)', textTransform: 'uppercase', letterSpacing: '0.15em' }}>
                      Danger Zone
                    </span>
                  </div>
                  <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '20px', lineHeight: '1.6' }}>
                    Sudo mode grants the AI unrestricted access to execute system commands. Use with caution.
                  </p>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div>
                      <p style={{ fontSize: '13px', fontWeight: 500, color: 'var(--text-secondary)' }}>Unrestricted System Access</p>
                      <p style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>Currently: {isSudo ? 'ACTIVE' : 'INACTIVE'}</p>
                    </div>
                    <button
                      onClick={() => setIsSudo(!isSudo)}
                      style={{
                        padding: '8px 18px',
                        borderRadius: '8px',
                        border: `1px solid ${isSudo ? 'var(--red-600)' : 'var(--border-default)'}`,
                        background: isSudo ? 'var(--red-600)' : 'transparent',
                        color: isSudo ? '#fff' : 'var(--text-muted)',
                        fontFamily: 'var(--font-mono)',
                        fontSize: '11px',
                        letterSpacing: '0.08em',
                        textTransform: 'uppercase',
                        cursor: 'pointer',
                        transition: 'all 0.2s',
                      }}
                    >
                      {isSudo ? 'Deactivate' : 'Activate'}
                    </button>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* ── BOOT SCREEN ───────────────────────────────────────── */}
      <AnimatePresence>
        {isBooting && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0, transition: { duration: 0.5 } }}
            style={{
              position: 'fixed', inset: 0, zIndex: 100,
              background: 'var(--bg-void)',
              display: 'flex', flexDirection: 'column',
              alignItems: 'center', justifyContent: 'center',
            }}
          >
            {/* Background ambience */}
            <div style={{
              position: 'absolute', top: '-20%', left: '20%',
              width: '60%', height: '60%',
              background: 'radial-gradient(ellipse, rgba(109,40,217,0.12) 0%, transparent 70%)',
              animation: 'pulse-violet 4s ease-in-out infinite',
              pointerEvents: 'none',
            }} />

            {/* Orbital spinner */}
            <div style={{ position: 'relative', width: '120px', height: '120px' }}>
              <div style={{
                position: 'absolute', inset: 0,
                borderRadius: '50%',
                border: '1.5px solid transparent',
                borderTopColor: 'rgba(109,40,217,0.5)',
                borderLeftColor: 'rgba(109,40,217,0.2)',
                animation: 'spin-slow 3s linear infinite',
              }} />
              <div style={{
                position: 'absolute', inset: '8px',
                borderRadius: '50%',
                border: '1.5px solid transparent',
                borderBottomColor: 'rgba(34,211,238,0.5)',
                borderRightColor: 'rgba(34,211,238,0.2)',
                animation: 'spin-reverse 2s linear infinite',
              }} />
              <div style={{
                position: 'absolute', inset: '18px',
                borderRadius: '50%',
                border: '1px solid rgba(109,40,217,0.15)',
              }} />
              <div style={{
                position: 'absolute', inset: 0,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}>
                <Zap size={28} color="var(--violet-400)" style={{ filter: 'drop-shadow(0 0 8px rgba(139,92,246,0.6))' }} />
              </div>
            </div>

            {/* Brand */}
            <div style={{ marginTop: '40px', textAlign: 'center' }}>
              <h1 style={{
                fontFamily: 'var(--font-display)',
                fontSize: '22px',
                fontWeight: 700,
                letterSpacing: '0.35em',
                textTransform: 'uppercase',
                color: 'var(--text-primary)',
              }}>
                ShadowForge
              </h1>
              <div style={{ width: '40px', height: '1px', background: 'var(--border-default)', margin: '12px auto' }} />
              <motion.p
                key={bootMessage}
                initial={{ opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
                style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: '11px',
                  color: 'var(--violet-300)',
                  letterSpacing: '0.05em',
                  opacity: 0.75,
                }}
              >
                {bootMessage}
              </motion.p>
            </div>

            {/* Progress bar */}
            <div style={{ position: 'absolute', bottom: '48px', left: 0, right: 0 }}>
              <div style={{ maxWidth: '280px', margin: '0 auto' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
                    Awakening Kernel
                  </span>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--text-muted)' }}>
                    AUTO
                  </span>
                </div>
                <div style={{ height: '2px', background: 'rgba(255,255,255,0.05)', borderRadius: '2px', overflow: 'hidden' }}>
                  <motion.div
                    animate={{ width: ['15%', '75%', '45%', '90%'] }}
                    transition={{ duration: 12, repeat: Infinity, ease: 'easeInOut' }}
                    style={{
                      height: '100%',
                      background: 'linear-gradient(90deg, var(--violet-700), var(--cyan-400))',
                      borderRadius: '2px',
                      boxShadow: '0 0 8px rgba(139,92,246,0.5)',
                    }}
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
