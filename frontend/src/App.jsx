import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Navbar           from './components/Navbar'
import Dashboard        from './pages/Dashboard'
import DueDiligence     from './pages/DueDiligence'
import Compliance       from './pages/Compliance'
import CreditRisk       from './pages/CreditRisk'
import Audit            from './pages/Audit'
import BusinessAdvisor  from './pages/BusinessAdvisor'
import Compare          from './pages/Compare'
import History          from './pages/History'
import Analytics        from './pages/Analytics'
import SynthGuardChat   from './components/SynthGuardChat'

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex min-h-screen bg-gray-50">
        <Navbar />
        <main className="flex-1 overflow-auto">
          <Routes>
            <Route path="/"                 element={<Dashboard />}       />
            <Route path="/due-diligence"    element={<DueDiligence />}    />
            <Route path="/compliance"       element={<Compliance />}      />
            <Route path="/credit-risk"      element={<CreditRisk />}      />
            <Route path="/audit"            element={<Audit />}           />
            <Route path="/business-advisor" element={<BusinessAdvisor />} />
            <Route path="/compare"          element={<Compare />}         />
            <Route path="/history"          element={<History />}         />
            <Route path="/analytics"        element={<Analytics />}       />
            <Route path="*" element={
              <div className="flex items-center justify-center h-full">
                <div className="text-center">
                  <p className="text-4xl font-bold text-gray-200">404</p>
                  <p className="text-gray-400 mt-2">Page introuvable</p>
                </div>
              </div>
            } />
          </Routes>
        </main>

        {/* Chatbot IA flottant — disponible sur toutes les pages */}
        <SynthGuardChat />
      </div>
    </BrowserRouter>
  )
}