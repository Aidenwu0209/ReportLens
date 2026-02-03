import { Routes, Route } from 'react-router-dom';
import LandingUploadPage from './pages/LandingUploadPage';
import ProcessingPage from './pages/ProcessingPage';
import DashboardPage from './pages/DashboardPage';
import AdminConsolePage from './pages/AdminConsolePage';

export default function App() {
  return (
    <div className="min-h-screen bg-surface">
      <Routes>
        <Route path="/" element={<LandingUploadPage />} />
        <Route path="/jobs/:jobId" element={<ProcessingPage />} />
        <Route path="/docs/:docId/v/:versionId" element={<DashboardPage />} />
        <Route path="/admin" element={<AdminConsolePage />} />
      </Routes>
    </div>
  );
}
