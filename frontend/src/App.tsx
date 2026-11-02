import { BrowserRouter, Routes, Route } from 'react-router-dom';
import './App.css';
import { HomePage } from './pages/HomePage';
import { WorkspacePage } from './pages/WorkspacePage';

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/repo/:id" element={<WorkspacePage />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
