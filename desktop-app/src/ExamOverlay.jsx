import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Target, Cpu, Activity } from 'lucide-react';

export default function ExamOverlay() {
  const [answer, setAnswer] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (window.electronAPI) {
      window.electronAPI.onExamAnswer((result) => {
        setLoading(false);
        setAnswer(result);
        
        // Auto-clear answer after 15 seconds
        setTimeout(() => setAnswer(''), 15000);
      });

      // Hook for when a capture starts
      window.electronAPI.onExamStart && window.electronAPI.onExamStart(() => {
        setLoading(true);
        setAnswer('');
      });
    }
  }, []);

  return (
    <div className="w-full h-full flex flex-col items-center justify-start pt-12 pointer-events-none select-none">
      <AnimatePresence>
        {loading && (
          <motion.div 
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0 }}
            className="flex items-center gap-3 glass px-6 py-3 rounded-full border-purple-500/50"
          >
             <Cpu size={16} className="text-purple-400 animate-spin" />
             <span className="text-xs font-bold tracking-[.3em] text-purple-200">ANALYZING TARGET...</span>
          </motion.div>
        )}

        {answer && (
          <motion.div 
            initial={{ opacity: 0, y: -20, filter: 'blur(10px)' }}
            animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
            exit={{ opacity: 0, y: -20, filter: 'blur(10px)' }}
            className="glass-card mt-4 border-red-500/40 shadow-[0_0_30px_rgba(255,0,0,0.2)] relative overflow-hidden"
            style={{ maxWidth: '90%' }}
          >
            {/* Header / HUD Markers */}
            <div className="flex items-center justify-between mb-3 border-b border-red-500/20 pb-2">
               <div className="flex items-center gap-2 text-[10px] font-bold text-red-400 tracking-tighter">
                  <Target size={12} />
                  DECODED_OUTPUT_v2.5
               </div>
               <div className="flex items-center gap-2">
                  <Activity size={10} className="text-red-500/50" />
                  <div className="w-12 h-1 bg-red-500/20 rounded-full overflow-hidden">
                     <motion.div 
                        initial={{ x: '-100%' }}
                        animate={{ x: '100%' }}
                        transition={{ repeat: Infinity, duration: 1.5, ease: 'linear' }}
                        className="w-1/2 h-full bg-red-500"
                     />
                  </div>
               </div>
            </div>

            {/* Content */}
            <div className="text-lg font-bold text-red-500 filter drop-shadow-[0_0_5px_rgba(255,0,0,0.5)]">
               {answer}
            </div>

            {/* Footer */}
            <div className="mt-3 flex justify-end text-[8px] font-mono text-red-500/40">
               AUTO_WIPE_IN_15S // SHADOWFORGE_CORE
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <style>{`
        .glass {
          background: rgba(13, 0, 24, 0.7);
          backdrop-filter: blur(12px);
          -webkit-backdrop-filter: blur(12px);
          border: 1px solid rgba(102, 0, 204, 0.25);
        }
        .glass-card {
          background: rgba(26, 0, 48, 0.8);
          backdrop-filter: blur(12px);
          -webkit-backdrop-filter: blur(12px);
          border: 1px solid rgba(102, 0, 204, 0.25);
          border-radius: 12px;
          padding: 16px 24px;
        }
      `}</style>
    </div>
  );
}
