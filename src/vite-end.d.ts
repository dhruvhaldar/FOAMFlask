/// <reference types="vite/client" />
/// <reference types="plotly.js" />

// Add type declarations for plotly.js
declare module 'plotly.js' {
  const Plotly: any;
  export = Plotly;
}