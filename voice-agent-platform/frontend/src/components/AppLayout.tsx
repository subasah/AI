import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { Building2, LayoutDashboard, PhoneCall, Sparkles, LogOut, ScrollText } from 'lucide-react'

const links = [
  { to: '/', label: 'Overview', icon: LayoutDashboard },
  { to: '/companies', label: 'Companies', icon: Building2 },
  { to: '/agents', label: 'Voice Agents', icon: PhoneCall },
  { to: '/calls', label: 'Call debug', icon: ScrollText },
  { to: '/create', label: 'Create & Sell', icon: Sparkles },
]

export default function AppLayout() {
  const navigate = useNavigate()

  function logout() {
    localStorage.removeItem('ava_access')
    navigate('/login')
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">
            Aether<span>Voice</span>
          </div>
          <div className="brand-sub">Industry-agnostic agent control plane</div>
        </div>
        <nav className="nav">
          {links.map(({ to, label, icon: Icon }) => (
            <NavLink key={to} to={to} end={to === '/'} className={({ isActive }) => (isActive ? 'active' : '')}>
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.55rem' }}>
                <Icon size={16} />
                {label}
              </span>
            </NavLink>
          ))}
        </nav>
        <button className="btn btn-ghost" onClick={logout} style={{ marginTop: 'auto' }}>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.45rem' }}>
            <LogOut size={16} /> Sign out
          </span>
        </button>
      </aside>
      <main className="main fade-in">
        <Outlet />
      </main>
    </div>
  )
}
