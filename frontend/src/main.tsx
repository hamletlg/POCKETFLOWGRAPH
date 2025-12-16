import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

console.log("Main.tsx executing...");

try {
  const root = document.getElementById('root');
  console.log("Root element:", root);
  if (root) {
    createRoot(root).render(
      <StrictMode>
        <App />
      </StrictMode>,
    )
  } else {
    console.error("Root element not found!");
  }
} catch (e) {
  console.error("Error in main.tsx render:", e);
}
