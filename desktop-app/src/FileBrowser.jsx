import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Folder, File as FileIcon, Archive, Cpu, Search, Sparkles } from 'lucide-react';

export default function FileBrowser() {
  const [files, setFiles] = useState([]);
  const [currentPath, setCurrentPath] = useState('');
  const [status, setStatus] = useState('Idle');

  useEffect(() => {
    loadFiles();
  }, []);

  const loadFiles = async (path = '') => {
    if (window.electronAPI) {
      const res = await window.electronAPI.readDir(path);
      if (res.success) {
        setCurrentPath(res.path);
        setFiles(res.files);
      }
    } else {
        // Fallback for browser dev mode
        setCurrentPath('C:/Users/user/Documents');
        setFiles(['ProjectFolder', 'test_data.zip', 'notes.txt', 'config.json']);
    }
  };

  const handleAction = async (fileName) => {
    if (fileName.endsWith('.zip')) {
        setStatus(`Instructing AI to extract ${fileName}...`);
        setTimeout(async () => {
             if (window.electronAPI) {
                 const res = await window.electronAPI.extractZip(
                     `${currentPath}/${fileName}`, 
                     `${currentPath}/extracted_${fileName}`
                 );
                 setStatus(res.message);
             } else setStatus(`Extracted ${fileName} successfully.`);
        }, 1500);
    } else {
        setStatus(`AI Vision requested for: ${fileName}`);
    }
  };

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex flex-col h-full bg-[#13141c] rounded-3xl border border-white/5 shadow-xl overflow-hidden">
      <div className="flex justify-between items-center px-6 py-5 border-b border-white/5 bg-[#0b0c10]">
         <div className="flex flex-col">
           <h2 className="text-xl font-medium text-slate-100 flex items-center gap-2">
             <Cpu size={20} className="text-indigo-400" /> System Integration
           </h2>
           <span className="text-sm text-slate-400 mt-1">AI Direct Path: {currentPath || "Connecting..."}</span>
         </div>
         <div className="bg-indigo-500/10 text-indigo-400 px-4 py-2 rounded-xl text-xs font-mono flex items-center gap-2 border border-indigo-500/20 shadow-sm">
            <Sparkles size={14} /> AI DIRECTORY CONTROL: ONLINE
         </div>
      </div>
      
      <div className="flex-1 overflow-y-auto custom-scrollbar p-4 bg-gradient-to-b from-transparent to-black/20">
        <div className="grid grid-cols-1 gap-2">
            {files.map((f, i) => (
            <div key={i} onClick={() => handleAction(f)} className="flex justify-between items-center p-4 bg-[#0b0c10]/50 hover:bg-[#1e1e24] rounded-2xl cursor-pointer transition border border-transparent hover:border-white/10 group">
                <div className="flex items-center gap-4">
                    <div className="p-2 rounded-xl bg-white/5 text-slate-400 group-hover:text-indigo-400 group-hover:bg-indigo-500/10 transition">
                        {f.includes('.') ? (f.endsWith('.zip') ? <Archive size={20} /> : <FileIcon size={20} />) : <Folder size={20} />}
                    </div>
                    <span className="text-slate-200 font-medium tracking-wide">{f}</span>
                </div>
                {f.endsWith('.zip') && (
                    <span className="text-xs bg-purple-500/10 border border-purple-500/20 text-purple-400 px-3 py-1.5 rounded-lg opacity-0 group-hover:opacity-100 transition shadow-sm">
                        Extract via AI
                    </span>
                )}
            </div>
            ))}
        </div>
      </div>

      {status !== 'Idle' && (
         <div className="bg-[#0b0c10] border-t border-white/5 p-4 text-sm flex gap-3 items-center text-slate-300">
            <div className="w-2 h-2 bg-indigo-500 rounded-full animate-pulse shadow-[0_0_8px_rgba(99,102,241,0.8)]"></div>
            <span className="font-mono text-xs text-indigo-200">{status}</span>
         </div>
      )}
    </motion.div>
  );
}
