import { Navigate, Outlet, Route, Routes } from 'react-router-dom'
import AppLayout from './components/AppLayout'
import LoginPage from './pages/LoginPage'
import OverviewPage from './pages/OverviewPage'
import CompaniesPage from './pages/CompaniesPage'
import AgentsPage from './pages/AgentsPage'
import CreateAgentPage from './pages/CreateAgentPage'
import AgentDetailPage from './pages/AgentDetailPage'

function RequireAuth() {
  const ok = localStorage.getItem('ava_access')
  if (!ok) return <Navigate to="/login" replace />
  return <Outlet />
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<RequireAuth />}>
        <Route element={<AppLayout />}>
          <Route path="/" element={<OverviewPage />} />
          <Route path="/companies" element={<CompaniesPage />} />
          <Route path="/agents" element={<AgentsPage />} />
          <Route path="/agents/:id" element={<AgentDetailPage />} />
          <Route path="/create" element={<CreateAgentPage />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
