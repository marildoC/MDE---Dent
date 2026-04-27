import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { listAuditLogs } from '../api/audit.js'
import { useAuth } from '../auth/useAuth.js'

function formatDateTime(value) {
  if (!value) {
    return ''
  }
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return value
  }
  return date.toLocaleString()
}

function formatDetails(details) {
  if (!details || Object.keys(details).length === 0) {
    return 'No details'
  }
  return Object.entries(details)
    .map(([key, value]) => `${key}: ${Array.isArray(value) ? value.join(', ') : value}`)
    .join(' | ')
}

export default function AuditLogPage() {
  const { logout } = useAuth()
  const [auditLogs, setAuditLogs] = useState([])
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    let isMounted = true

    listAuditLogs()
      .then((data) => {
        if (isMounted) {
          setAuditLogs(data)
          setError('')
        }
      })
      .catch((err) => {
        if (isMounted) {
          setError(err.message)
        }
      })
      .finally(() => {
        if (isMounted) {
          setIsLoading(false)
        }
      })

    return () => {
      isMounted = false
    }
  }, [])

  return (
    <main className="app-shell">
      <header className="top-bar">
        <div>
          <p className="eyebrow">Admin area</p>
          <h1>Audit Logs</h1>
        </div>
        <div className="button-row">
          <Link className="secondary-link" to="/admin">
            Dashboard
          </Link>
          <button className="secondary-button" type="button" onClick={logout}>
            Logout
          </button>
        </div>
      </header>

      {error ? <p className="form-error page-error">{error}</p> : null}

      <section className="dashboard-panel audit-panel">
        <div>
          <p className="eyebrow">Traceability</p>
          <h2>System Audit Trail</h2>
        </div>
        {isLoading ? <p>Loading audit logs...</p> : null}
        {!isLoading && auditLogs.length === 0 ? <p>No audit logs yet.</p> : null}
        <ul className="resource-list audit-list">
          {auditLogs.map((log) => (
            <li key={log.id}>
              <span>
                <strong>{log.action}</strong>
                <small>{formatDateTime(log.created_at)}</small>
                <small>
                  Actor: {log.actor_detail?.username || 'System'} | Target: {log.target_type} #
                  {log.target_id}
                </small>
                <small>{log.target_repr}</small>
                <small>{formatDetails(log.details)}</small>
              </span>
            </li>
          ))}
        </ul>
      </section>
    </main>
  )
}
