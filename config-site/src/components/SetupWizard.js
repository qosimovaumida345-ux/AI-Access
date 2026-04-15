"use client";

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ShieldAlert, Cpu, Download, Sparkles, CheckCircle2, ChevronRight, Fingerprint } from 'lucide-react';
import { QRCodeSVG } from 'qrcode.react';

const steps = [
  { id: 'welcome', title: 'Welcome to AI-Access' },
  { id: 'provider', title: 'Select AI Core' },
  { id: 'verify', title: 'Verifying Secure Connection' },
  { id: 'install', title: 'Deploy to Devices' }
];

export default function SetupWizard() {
  const [currentStep, setCurrentStep] = useState(0);
  const [provider, setProvider] = useState('groq');
  const [deviceToken, setDeviceToken] = useState('TOKEN_NOT_READY');
  const [isVerifying, setIsVerifying] = useState(false);
  const [statusMessage, setStatusMessage] = useState('');
  const backendBaseUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:5000';
  const releasesUrl = process.env.NEXT_PUBLIC_RELEASES_URL || '#';

  const handleNext = async () => {
    if (currentStep === 1) {
      setIsVerifying(true);
      setStatusMessage('');
      setCurrentStep(2);

      try {
        const statusRes = await fetch(`${backendBaseUrl}/api/config/status`);
        if (!statusRes.ok) throw new Error('Core API is unreachable');

        const token = "AI-" + Math.random().toString(36).substring(2, 12).toUpperCase();
        const bindRes = await fetch(`${backendBaseUrl}/api/config/bind`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            deviceToken: token,
            settings: { defaultProvider: provider }
          })
        });
        if (!bindRes.ok) throw new Error('Device bind failed');

        setDeviceToken(token);
        setStatusMessage('Connected to secure backend. Keys stay server-side.');
        setCurrentStep(3);
      } catch (e) {
        setStatusMessage(`Verification warning: ${e.message}`);
        setCurrentStep(3);
      } finally {
        setIsVerifying(false);
      }
      return;
    }
    
    if (currentStep < steps.length - 1) {
      setCurrentStep(prev => prev + 1);
    }
  };

  return (
    <div className="w-full max-w-2xl">
      {/* Wizard Header */}
      <div className="flex items-center justify-between mb-8 px-4 relative z-10">
        {steps.map((step, idx) => (
          <div key={idx} className={`flex flex-col items-center gap-2 ${idx <= currentStep ? 'text-primary' : 'text-slate-500'}`}>
            <div className={`w-8 h-8 rounded-full flex items-center justify-center border-2 
              ${idx < currentStep ? 'bg-primary border-primary text-white' : 
                idx === currentStep ? 'border-primary shadow-[0_0_15px_rgba(59,130,246,0.6)]' : 'border-slate-700'}`}>
              {idx < currentStep ? <CheckCircle2 size={16} /> : idx + 1}
            </div>
            <span className="text-xs font-semibold hidden md:block">{step.title}</span>
          </div>
        ))}
        {/* Progress line */}
        <div className="absolute top-4 left-[10%] right-[10%] h-[2px] bg-slate-800 -z-10">
          <motion.div 
            className="h-full bg-primary"
            initial={{ width: '0%' }}
            animate={{ width: `${(currentStep / (steps.length - 1)) * 100}%` }}
            transition={{ duration: 0.5 }}
          />
        </div>
      </div>

      {/* Glass Panel Content */}
      <div className="glass-panel p-8 relative overflow-hidden min-h-[400px] flex flex-col justify-between">
        <AnimatePresence mode="wait">
          
          {/* STEP 0: Welcome */}
          {currentStep === 0 && (
            <motion.div 
              key="step0"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              className="flex-1 flex flex-col justify-center gap-6"
            >
              <div className="flex gap-4 items-center">
                <div className="p-4 bg-primary/20 rounded-2xl border border-primary/30 text-primary">
                  <Fingerprint size={40} />
                </div>
                <div>
                  <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-indigo-400">
                    ShadowForge / AI-Access
                  </h1>
                  <p className="text-slate-400">Universal System-Level AI Companion</p>
                </div>
              </div>
              <p className="text-slate-300 leading-relaxed text-lg">
                Are you ready to initialize the system? You are about to bind a powerful AI that can interact with your active screen, manage files, and act on your behalf across Desktop and Mobile devices.
              </p>
              <div className="flex items-center gap-3 p-4 bg-red-500/10 border border-red-500/20 rounded-lg text-red-200">
                <ShieldAlert size={24} className="text-red-400 flex-shrink-0" />
                <p className="text-sm">Warning: Enabling Exam Mode grants the AI continuous buffer-access to your visual stack. Proceed with responsibility.</p>
              </div>
            </motion.div>
          )}

          {/* STEP 1: Provider */}
          {currentStep === 1 && (
            <motion.div 
              key="step1"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              className="flex-1 flex flex-col gap-6"
            >
              <div>
                <h2 className="text-2xl font-bold flex items-center gap-2">
                  <Cpu /> Configure Engine
                </h2>
                <p className="text-slate-400 text-sm mt-1">Your API keys are encrypted and stored ONLY on the core backend, never compiled into the App binaries.</p>
              </div>

              <div className="grid grid-cols-2 gap-4">
                {['groq', 'gemini', 'openrouter', 'together', 'mistral', 'cohere'].map((p) => (
                  <button 
                    key={p}
                    onClick={() => setProvider(p)}
                    className={`p-4 rounded-xl border text-left transition-all ${
                      provider === p 
                      ? 'border-primary bg-primary/20 shadow-[0_0_15px_rgba(59,130,246,0.3)]' 
                      : 'border-slate-700 bg-black/20 hover:border-slate-500'
                    }`}
                  >
                    <div className="font-bold capitalize">{p}</div>
                    <div className="text-xs text-slate-400 mt-1">Standard profile</div>
                  </button>
                ))}
              </div>

              <div className="mt-4">
                <div className="w-full p-4 rounded-xl bg-blue-500/10 border border-blue-500/30 text-sm text-blue-100">
                  API key input is disabled in client UI. Keys are read only from backend environment variables.
                </div>
              </div>
            </motion.div>
          )}

          {/* STEP 2: Verify */}
          {currentStep === 2 && (
            <motion.div 
              key="step2"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 1.1 }}
              className="flex-1 flex flex-col items-center justify-center gap-6 text-center"
            >
              <div className="relative w-24 h-24">
                <motion.div 
                  animate={{ rotate: 360 }}
                  transition={{ repeat: Infinity, duration: 2, ease: "linear" }}
                  className="absolute inset-0 rounded-full border-t-2 border-r-2 border-primary"
                />
                <motion.div 
                  animate={{ rotate: -360 }}
                  transition={{ repeat: Infinity, duration: 3, ease: "linear" }}
                  className="absolute inset-2 rounded-full border-b-2 border-l-2 border-indigo-400"
                />
                <div className="absolute inset-0 flex items-center justify-center">
                  <Sparkles className="text-primary animate-pulse" />
                </div>
              </div>
              <div>
                <h3 className="text-xl font-bold">Establishing Secure Uplink</h3>
                <p className="text-slate-400 mt-2">Validating key integrity with core server...</p>
              </div>
            </motion.div>
          )}

          {/* STEP 3: Install/Download */}
          {currentStep === 3 && (
            <motion.div 
              key="step3"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex-1 flex flex-col gap-6"
            >
              <div className="text-center">
                <div className="mx-auto w-16 h-16 bg-green-500/20 text-green-400 rounded-full flex items-center justify-center mb-4">
                  <CheckCircle2 size={32} />
                </div>
                <h2 className="text-3xl font-bold">System Bound</h2>
                <p className="text-slate-400 mt-2">Your API profile is ready. Use this token or scan to sync devices.</p>
                {statusMessage ? <p className="text-xs text-blue-300 mt-3">{statusMessage}</p> : null}
              </div>

              <div className="bg-black/40 p-4 rounded-xl border border-slate-700 flex flex-col items-center gap-4">
                <div className="text-xs uppercase tracking-widest text-slate-500">Device Sync Token</div>
                <div className="text-2xl font-mono text-primary tracking-widest bg-primary/10 px-6 py-2 rounded-lg">
                  {deviceToken}
                </div>
                
                {/* QR Code Demo */}
                <div className="p-4 bg-white rounded-xl mt-2 relative">
                  <QRCodeSVG value={deviceToken} size={150} level={"H"} />
                  {/* Small absolute logo inside QR could go here */}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4 mt-2">
                 <a href={releasesUrl} target="_blank" rel="noreferrer" className="flex items-center justify-center gap-2 p-3 bg-white/5 hover:bg-white/10 rounded-lg border border-slate-700 transition">
                    <Download size={18} /> Desktop (.exe)
                 </a>
                 <a href={releasesUrl} target="_blank" rel="noreferrer" className="flex items-center justify-center gap-2 p-3 bg-white/5 hover:bg-white/10 rounded-lg border border-slate-700 transition">
                    <Download size={18} /> Mobile (.apk)
                 </a>
              </div>
            </motion.div>
          )}

        </AnimatePresence>

        {/* Footer Navigation */}
        {currentStep < 2 && (
          <div className="mt-8 flex justify-end shrink-0">
            <button 
              onClick={handleNext}
              className="btn-primary flex items-center gap-2 px-8 py-3 rounded-lg font-bold"
            >
              {currentStep === 0 ? "Initialize Setup" : "Verify & Bind"} <ChevronRight size={18} />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
