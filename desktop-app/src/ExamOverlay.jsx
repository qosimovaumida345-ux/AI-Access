import React, { useEffect, useState } from 'react';

export default function ExamOverlay() {
  const [answer, setAnswer] = useState('');

  useEffect(() => {
    if (window.electronAPI) {
      window.electronAPI.onExamAnswer((result) => {
        setAnswer(result);
        
        // Auto-clear answer after 10 seconds to keep screen clean
        setTimeout(() => setAnswer(''), 10000);
      });
    }
  }, []);

  if (!answer) return null;

  return (
    <div style={{
      width: '100%',
      height: '100%',
      display: 'flex',
      alignItems: 'flex-start',
      justifyContent: 'center',
      paddingTop: '10px',
      WebkitAppRegion: 'no-drag'
    }}>
      <div style={{
        color: '#ff3333',         // The requested red text
        backgroundColor: 'rgba(0,0,0,0.6)', 
        padding: '5px 15px',
        borderRadius: '8px',
        fontWeight: 'bold',
        fontSize: '18px',
        border: '1px solid #ff3333',
        boxShadow: '0 0 10px rgba(255,51,51,0.5)',
        maxWidth: '80%',
        textAlign: 'center'
      }}>
        {answer}
      </div>
    </div>
  );
}
