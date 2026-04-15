import React, { useMemo, useState } from 'react';
import { Clipboard, Code2, Check, Download, Terminal } from 'lucide-react';

export default function CodeWorkspace() {
  const [code, setCode] = useState('// AI-Access workspace\n\nexport function greet(name) {\n  return `Hello, ${name}!`;\n}\n');
  const [copied, setCopied] = useState(false);
  const [saveStatus, setSaveStatus] = useState('Not saved');
  const [logs, setLogs] = useState(['Workspace ready.']);

  const lineCount = useMemo(() => code.split('\n').length, [code]);

  const copyCode = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const saveFile = () => {
    const blob = new Blob([code], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'ai-access-snippet.js';
    link.click();
    URL.revokeObjectURL(url);
    setSaveStatus(`Saved at ${new Date().toLocaleTimeString()}`);
    setLogs((prev) => [`Saved ai-access-snippet.js`, ...prev].slice(0, 6));
  };

  return (
    <div className="flex flex-col h-full bg-[#13141c] rounded-2xl border border-white/5 overflow-hidden shadow-xl">
      {/* Editor Header */}
      <div className="flex justify-between items-center px-4 py-3 bg-[#0b0c10] border-b border-white/5">
        <div className="flex items-center gap-2 text-indigo-400">
           <Code2 size={18} />
           <span className="font-medium text-sm">Workspace Editor</span>
        </div>
        <div className="flex gap-2">
           <button onClick={copyCode} className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-slate-300 text-xs transition">
             {copied ? <Check size={14} className="text-green-400" /> : <Clipboard size={14} />}
             {copied ? 'Copied' : 'Copy'}
           </button>
           <button onClick={saveFile} className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-indigo-600/20 text-indigo-400 hover:bg-indigo-600/30 text-xs transition">
             <Download size={14} /> Save
           </button>
        </div>
      </div>

      {/* Editor Area */}
      <div className="flex-1 relative">
         <div className="absolute top-0 left-0 bottom-0 w-12 bg-black/20 border-r border-white/5 flex flex-col items-center py-4 text-xs text-slate-600 font-mono select-none">
            {Array.from({ length: lineCount }).map((_, i) => <div key={i} className="mb-1">{i + 1}</div>)}
         </div>
         <textarea 
            value={code}
            onChange={e => setCode(e.target.value)}
            className="w-full h-full bg-transparent text-slate-300 font-mono text-sm p-4 pl-16 focus:outline-none resize-none custom-scrollbar"
            spellCheck="false"
         />
      </div>

      {/* Terminal View */}
      <div className="h-48 bg-[#08080a] border-t border-white/5 p-4 font-mono text-xs overflow-y-auto custom-scrollbar">
         <div className="text-slate-500 mb-2 flex items-center gap-2"><Terminal size={14} /> Workspace Output</div>
         <div className="text-indigo-300 mb-2">Status: {saveStatus}</div>
         {logs.map((line, idx) => (
           <div key={idx} className="text-slate-300 mt-1">{line}</div>
         ))}
      </div>
    </div>
  );
}
