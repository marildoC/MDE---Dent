import { useAuth } from '../auth/useAuth.js'

const dashboardCopy = {
  patient: {
    eyebrow: 'Patient area',
    title: 'Patient Dashboard',
    body: 'No active follow-up case yet.',
  },
  staff: {
    eyebrow: 'Dentist and staff area',
    title: 'Dentist/Staff Dashboard',
    body: 'No escalated cases yet.',
  },
  admin: {
    eyebrow: 'Admin area',
    title: 'Admin Dashboard',
    body: 'Workflow management placeholder.',
  },
}

function DashboardLayout({ variant }) {
  const { logout, user } = useAuth()
  const copy = dashboardCopy[variant]

  return (
    <main className="app-shell">
      <header className="top-bar">
        <div>
          <p className="eyebrow">DentCare-MDE</p>
          <h1>{copy.title}</h1>
        </div>
        <button className="secondary-button" type="button" onClick={logout}>
          Logout
        </button>
      </header>

      <section className="dashboard-panel">
        <div>
          <p className="eyebrow">{copy.eyebrow}</p>
          <h2>{copy.body}</h2>
        </div>
        <dl className="identity-list">
          <div>
            <dt>User</dt>
            <dd>{user.username}</dd>
          </div>
          <div>
            <dt>Role</dt>
            <dd>{user.role}</dd>
          </div>
        </dl>
      </section>
    </main>
  )
}

export function PatientDashboard() {
  return <DashboardLayout variant="patient" />
}

export function StaffDashboard() {
  return <DashboardLayout variant="staff" />
}

export function AdminDashboard() {
  return <DashboardLayout variant="admin" />
}
