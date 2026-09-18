import { Navigate, Route, Routes } from 'react-router-dom';

import Layout from './components/Layout.jsx';
import DashboardPage from './pages/dashboard/DashboardPage.jsx';
import EmergencyDetailPage from './pages/emergencies/EmergencyDetailPage.jsx';
import EmergencyListPage from './pages/emergencies/EmergencyListPage.jsx';
import InspectionListPage from './pages/inspections/InspectionListPage.jsx';
import IssueDetailPage from './pages/issues/IssueDetailPage.jsx';
import IssueListPage from './pages/issues/IssueListPage.jsx';
import RestroomDetailPage from './pages/restrooms/RestroomDetailPage.jsx';
import RestroomListPage from './pages/restrooms/RestroomListPage.jsx';

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/restrooms" element={<RestroomListPage />} />
        <Route path="/restrooms/:restroomId" element={<RestroomDetailPage />} />
        <Route path="/inspections" element={<InspectionListPage />} />
        <Route path="/issues" element={<IssueListPage />} />
        <Route path="/issues/:issueId" element={<IssueDetailPage />} />
        <Route path="/emergencies" element={<EmergencyListPage />} />
        <Route path="/emergencies/:eventId" element={<EmergencyDetailPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
