import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import ProtectedRoute  from './components/ProtectedRoute'
import Navbar          from './components/Navbar'
import Login           from './pages/Login'
import Dashboard       from './pages/Dashboard'
import DueDiligence    from './pages/DueDiligence'
import Compliance      from './pages/Compliance'
import CreditRisk      from './pages/CreditRisk'
import Audit           from './pages/Audit'
import BusinessAdvisor from './pages/BusinessAdvisor'
import Compare         from './pages/Compare'
import History         from './pages/History'
import Analytics       from './pages/Analytics'
import AdminUsers      from './pages/AdminUsers'
import SynthGuardChat  from './components/SynthGuardChat'

function AppLayout({ children }) {
  return (
    <div className="flex min-h-screen bg-gray-50">
      <Navbar />
      <main className="flex-1 overflow-auto">
        {children}
      </main>
      <SynthGuardChat />
    </div>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Route publique */}
          <Route path="/login" element={<Login />} />

          {/* Routes protégées */}
          <Route path="/" element={
            <ProtectedRoute>
              <AppLayout><Dashboard /></AppLayout>
            </ProtectedRoute>
          } />
          <Route path="/due-diligence" element={
            <ProtectedRoute><AppLayout><DueDiligence /></AppLayout></ProtectedRoute>
          } />
          <Route path="/compliance" element={
            <ProtectedRoute><AppLayout><Compliance /></AppLayout></ProtectedRoute>
          } />
          <Route path="/credit-risk" element={
            <ProtectedRoute><AppLayout><CreditRisk /></AppLayout></ProtectedRoute>
          } />
          <Route path="/audit" element={
            <ProtectedRoute><AppLayout><Audit /></AppLayout></ProtectedRoute>
          } />
          <Route path="/business-advisor" element={
            <ProtectedRoute><AppLayout><BusinessAdvisor /></AppLayout></ProtectedRoute>
          } />
          <Route path="/compare" element={
            <ProtectedRoute><AppLayout><Compare /></AppLayout></ProtectedRoute>
          } />
          <Route path="/history" element={
            <ProtectedRoute><AppLayout><History /></AppLayout></ProtectedRoute>
          } />
          <Route path="/analytics" element={
            <ProtectedRoute><AppLayout><Analytics /></AppLayout></ProtectedRoute>
          } />
          <Route path="/admin/users" element={
            <ProtectedRoute><AppLayout><AdminUsers /></AppLayout></ProtectedRoute>
          } />

          {/* Fallback */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}