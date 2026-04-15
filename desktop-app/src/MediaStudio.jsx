import React, { useState } from 'react';
import { Image as ImageIcon, Music, Wand2, Download } from 'lucide-react';

export default function MediaStudio() {
  const [prompt, setPrompt] = useState('');
  const [imageStatus, setImageStatus] = useState('Idle');
  const [audioStatus, setAudioStatus] = useState('Idle');

  const requestImage = () => {
    if (!prompt.trim()) return;
    setImageStatus('Queued');
    setTimeout(() => setImageStatus('Processing'), 700);
    setTimeout(() => setImageStatus('Complete'), 1800);
  };

  const requestAudio = () => {
    setAudioStatus('Queued');
    setTimeout(() => setAudioStatus('Synthesizing'), 700);
    setTimeout(() => setAudioStatus('Complete'), 1800);
  };

  return (
    <div className="flex flex-col h-full gap-6 overflow-y-auto custom-scrollbar">
       
       {/* Image Generator Section */}
       <div className="bg-[#13141c] rounded-3xl border border-white/5 p-6 shadow-xl relative overflow-hidden">
          <div className="absolute top-0 right-0 w-64 h-64 bg-indigo-500/10 blur-[80px] rounded-full pointer-events-none"></div>
          
          <div className="flex items-center gap-3 mb-6 relative z-10">
             <div className="w-10 h-10 rounded-xl bg-indigo-500/20 text-indigo-400 flex items-center justify-center">
                <ImageIcon size={20} />
             </div>
             <div>
               <h2 className="text-xl font-medium text-slate-100">Image Generation Studio</h2>
               <p className="text-sm text-slate-400">Powered by advanced diffusion models.</p>
             </div>
          </div>

          <div className="flex gap-4 relative z-10">
             <input value={prompt} onChange={(e) => setPrompt(e.target.value)} type="text" placeholder="Describe the image you want to create..." className="flex-1 bg-[#0b0c10] border border-white/10 rounded-2xl px-6 py-4 text-sm text-slate-200 focus:outline-none focus:border-indigo-500/50" />
             <button onClick={requestImage} className="bg-indigo-600 hover:bg-indigo-500 text-white px-8 rounded-2xl font-medium shadow-lg shadow-indigo-600/20 flex items-center gap-2 transition">
               <Wand2 size={18} /> Generate
             </button>
          </div>
          <div className="mt-3 text-xs text-indigo-300">Image Pipeline: {imageStatus}</div>

          {/* Sample Gallery */}
          <div className="mt-8 grid grid-cols-3 gap-4 relative z-10">
             {[1,2,3].map(i => (
                <div key={i} className="aspect-square bg-[#0b0c10] rounded-2xl border border-white/5 flex flex-col items-center justify-center text-slate-600 relative group overflow-hidden">
                   <ImageIcon size={32} className="opacity-20 mb-2" />
                   <span className="text-xs">Placeholder ID-{i}</span>
                   <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center backdrop-blur-sm">
                      <button className="bg-white/10 hover:bg-white/20 p-3 rounded-full text-white transition"><Download size={20}/></button>
                   </div>
                </div>
             ))}
          </div>
       </div>

       {/* Music & Audio Section */}
       <div className="bg-[#13141c] rounded-3xl border border-white/5 p-6 shadow-xl relative overflow-hidden">
          <div className="absolute bottom-0 left-0 w-64 h-64 bg-purple-500/10 blur-[80px] rounded-full pointer-events-none"></div>
          
          <div className="flex items-center gap-3 mb-6 relative z-10">
             <div className="w-10 h-10 rounded-xl bg-purple-500/20 text-purple-400 flex items-center justify-center">
                <Music size={20} />
             </div>
             <div>
               <h2 className="text-xl font-medium text-slate-100">Audio & Music Synthesis</h2>
               <p className="text-sm text-slate-400">Generate sound effects or background tracks.</p>
             </div>
          </div>

          <div className="bg-[#0b0c10] rounded-2xl border border-white/5 p-6 flex flex-col items-center justify-center py-12 relative z-10">
             <button onClick={requestAudio} className="w-40 h-12 bg-purple-600 rounded-xl flex items-center justify-center text-white hover:scale-105 transition shadow-lg shadow-purple-600/30 mb-4">
                Start audio task
             </button>
             <div className="w-full max-w-md h-2 bg-white/10 rounded-full overflow-hidden mb-2">
                <div className={`h-full bg-gradient-to-r from-purple-500 to-indigo-500 rounded-full transition-all duration-700 ${audioStatus === 'Idle' ? 'w-0' : audioStatus === 'Queued' ? 'w-1/4' : audioStatus === 'Synthesizing' ? 'w-2/3' : 'w-full'}`}></div>
             </div>
             <div className="flex justify-between w-full max-w-md text-xs text-slate-500">
                <span>Task</span>
                <span>{audioStatus}</span>
             </div>
          </div>
       </div>
    </div>
  );
}
