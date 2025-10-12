import React from 'react';
import Layout from './components/layout/Layout';
import { AppProvider } from './context/AppContext';
import "bootstrap/dist/css/bootstrap.min.css";
import '@mdi/font/css/materialdesignicons.min.css';

import './App.css'; // Import your global styles
import { ToasterProvider } from './Toaster/Toaster';
function App() {
  return (
    <ToasterProvider>
    <AppProvider>
      <Layout />
    </AppProvider>
    </ToasterProvider>
  );
}

export default App;