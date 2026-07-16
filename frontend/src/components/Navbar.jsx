import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard, Search, ShieldCheck, CreditCard,
  ClipboardList, Lightbulb, History, GitCompare, BarChart2, LogOut, Users
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { useNavigate } from 'react-router-dom'

const TEAL      = '#00B09B'
const TEAL_DARK = '#008C7A'
const TEAL_LITE = '#E6F7F5'

const SECTIONS = [
  {
    label: 'GÉNÉRAL',
    links: [
      { to: '/',          label: 'Dashboard',  icon: LayoutDashboard },
      { to: '/analytics', label: 'Analytics',  icon: BarChart2       },
      { to: '/history',   label: 'Historique', icon: History         },
      { to: '/compare',   label: 'Comparer',   icon: GitCompare      },
    ],
  },
  {
    label: 'MODULES IA',
    links: [
      { to: '/due-diligence',    label: 'Due Diligence',    icon: Search       },
      { to: '/compliance',       label: 'Compliance & AML', icon: ShieldCheck  },
      { to: '/credit-risk',      label: 'Credit Risk',      icon: CreditCard   },
      { to: '/audit',            label: 'Audit',            icon: ClipboardList},
      { to: '/business-advisor', label: 'Business Advisor', icon: Lightbulb   },
    ],
  },
]

export default function Navbar() {
  const { user, logout, isAdmin } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <aside className="w-60 min-h-screen bg-white flex flex-col"
           style={{ borderRight: '1px solid #E5E7EB' }}>

      {/* Logo */}
      <div className="px-5 py-5 flex items-center gap-3"
           style={{ borderBottom: '1px solid #E5E7EB' }}>
        <div className="w-9 h-9 rounded-lg flex items-center justify-center"
             style={{ background: TEAL }}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
            <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"
                  stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </div>
        <div>
          <p className="font-bold text-sm leading-tight" style={{ color: '#0A0A0A' }}>
            SynthGuard
          </p>
          <p className="text-xs leading-tight" style={{ color: '#9CA3AF' }}>
            Intelligence v2.0
          </p>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-5 overflow-y-auto">
        {SECTIONS.map(section => (
          <div key={section.label}>
            <p className="text-xs font-semibold px-3 mb-1.5 tracking-widest"
               style={{ color: '#D1D5DB' }}>
              {section.label}
            </p>
            <div className="space-y-0.5">
              {section.links.map(({ to, label, icon: Icon }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={to === '/'}
                  style={({ isActive }) => isActive ? {
                    background     : TEAL_LITE,
                    color          : TEAL,
                    borderLeft     : `3px solid ${TEAL}`,
                    paddingLeft    : '10px',
                  } : {}}
                  className={({ isActive }) =>
                    `flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-sm
                     font-medium transition-all
                     ${isActive
                       ? ''
                       : 'text-gray-500 hover:bg-gray-50 hover:text-gray-800'}`
                  }
                >
                  {({ isActive }) => (
                    <>
                      <Icon size={15}
                            style={{ color: isActive ? TEAL : '#9CA3AF' }}
                            className="flex-shrink-0 transition-colors" />
                      <span>{label}</span>
                    </>
                  )}
                </NavLink>
              ))}
            </div>
          </div>
        ))}
      </nav>

      {/* Footer — profil + logout */}
      <div className="px-4 py-4 space-y-1" style={{ borderTop: '1px solid #E5E7EB' }}>
        {isAdmin && (
          <button
            onClick={() => navigate('/admin/users')}
            className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs
                       text-gray-500 hover:bg-gray-50 hover:text-gray-800 transition">
            <Users size={14} />
            Gérer les utilisateurs
          </button>
        )}
        <div className="flex items-center justify-between px-3 py-2 rounded-lg
                        hover:bg-gray-50 transition cursor-pointer group">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-full flex items-center justify-center
                            text-xs font-bold text-white flex-shrink-0"
                 style={{ background: TEAL }}>
              {user?.avatar || user?.name?.[0] || '?'}
            </div>
            <div className="min-w-0">
              <p className="text-xs font-semibold text-gray-800 truncate">
                {user?.name || 'Utilisateur'}
              </p>
              <p className="text-xs text-gray-400 truncate">
                {user?.role === 'admin' ? 'Administrateur' : 'Utilisateur'}
              </p>
            </div>
          </div>
          <button onClick={handleLogout}
            title="Se déconnecter"
            className="p-1.5 rounded-lg text-gray-300 hover:text-red-500
                       hover:bg-red-50 transition opacity-0 group-hover:opacity-100">
            <LogOut size={13} />
          </button>
        </div>
      </div>
    </aside>
  )
}