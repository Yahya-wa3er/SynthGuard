import { NavLink } from 'react-router-dom'
import { BarChart2 } from 'lucide-react'
import {
  LayoutDashboard, Search, ShieldCheck, CreditCard,
  ClipboardList, Lightbulb, History, GitCompare
} from 'lucide-react'

const links = [
  { to: '/',                 label: 'Dashboard',        icon: LayoutDashboard },
  { to: '/due-diligence',    label: 'Due Diligence',    icon: Search          },
  { to: '/compliance',       label: 'Compliance & AML', icon: ShieldCheck     },
  { to: '/credit-risk',      label: 'Credit Risk',      icon: CreditCard      },
  { to: '/audit',            label: 'Audit',            icon: ClipboardList   },
  { to: '/business-advisor', label: 'Business Advisor', icon: Lightbulb       },
  { to: '/compare',          label: 'Comparer',         icon: GitCompare      },
  { to: '/history',          label: 'Historique',       icon: History         },
  { to: '/analytics',        label: 'Analytics',        icon: BarChart2       },
]

export default function Navbar() {
  return (
    <aside className="w-64 min-h-screen bg-white border-r border-gray-100 flex flex-col shadow-sm">
      <div className="p-6 border-b border-gray-100">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 bg-primary rounded-lg flex items-center justify-center">
            <span className="text-white font-bold text-lg">⬡</span>
          </div>
          <div>
            <p className="font-bold text-primary text-sm leading-tight">SynthGuard</p>
            <p className="text-xs text-gray-400 leading-tight">Intelligence</p>
          </div>
        </div>
      </div>
      <nav className="flex-1 p-4 space-y-1">
        {links.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all
               ${isActive
                 ? 'bg-blue-50 text-accent border-l-2 border-accent pl-[10px]'
                 : 'text-gray-500 hover:bg-gray-50 hover:text-gray-800'}`
            }
          >
            <Icon size={16} />
            {label}
          </NavLink>
        ))}
      </nav>
      <div className="p-4 border-t border-gray-100">
        <p className="text-xs text-gray-400 text-center">SynthGuard Intelligence v2.0</p>
      </div>
    </aside>
  )
}