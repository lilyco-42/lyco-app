import React from 'react';
import App from './App.tsx';  // .tsx is required: on Windows './App' resolves to app.json

export default {
  title: 'App Root',
  component: App,
};

export const ChatTab = () => <App />;
