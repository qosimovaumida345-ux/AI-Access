import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import ExamOverlay from './ExamOverlay';
import './index.css';

// Simple router based on hash, useful for Electron multi-window architecture
const hash = window.location.hash;

const root = ReactDOM.createRoot(document.getElementById('root'));

if (hash === '#/overlay') {
  root.render(
    <React.StrictMode>
      <ExamOverlay />
    </React.StrictMode>
  );
} else {
  root.render(
    <React.StrictMode>
      <App />
    </React.StrictMode>
  );
}
