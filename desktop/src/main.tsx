import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';

import './styles/global.css';
import './styles/antdOverrides.css';

import App from './App';

// Apply persisted theme or default to dark
const stored = localStorage.getItem('novem-app');
const parsed = stored ? JSON.parse(stored)?.state : null;
const theme = parsed?.themeMode || 'dark';
document.documentElement.setAttribute('data-theme', theme);
if (parsed?.zoomLevel && parsed.zoomLevel !== 100) {
  document.documentElement.style.setProperty('--app-zoom', String(parsed.zoomLevel / 100));
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
