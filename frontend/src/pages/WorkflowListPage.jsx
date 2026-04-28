import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { createWorkflow, listWorkflows } from '../api/workflows.js'
import { useAuth } from '../auth/useAuth.js'
import { formatConstant, statusClass } from '../utils/display.js'

const initialForm = {
  name: 'Post-Extraction Follow-Up',
  treatment_type: 'POST_EXTRACTION',
  description: '',
}

export default function WorkflowListPage() {
  const navigate = useNavigate()
  const { logout } = useAuth()
  const [workflows, setWorkflows] = useState([])
  const [form, setForm] = useState(initialForm)
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(true)
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {
    listWorkflows()
      .then(setWorkflows)
      .catch((err) => setError(err.message))
      .finally(() => setIsLoading(false))
  }, [])

  const handleChange = (event) => {
    setForm((current) => ({
      ...current,
      [event.target.name]: event.target.value,
    }))
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    setIsSubmitting(true)
    setError('')

    try {
      const workflow = await createWorkflow({ ...form, status: 'DRAFT' })
      navigate(`/admin/workflows/${workflow.id}`)
    } catch (err) {
      setError(err.message)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <main className="app-shell">
      <header className="top-bar">
        <div>
          <p className="eyebrow">Admin area</p>
          <h1>Workflow Management</h1>
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

      <section className="split-layout">
        <form className="panel-form" onSubmit={handleSubmit}>
          <h2>Create Workflow</h2>
          <label>
            Name
            <input name="name" onChange={handleChange} required value={form.name} />
          </label>
          <label>
            Treatment type
            <select name="treatment_type" onChange={handleChange} value={form.treatment_type}>
              <option value="POST_EXTRACTION">Post-Extraction Follow-Up</option>
            </select>
          </label>
          <label>
            Description
            <textarea name="description" onChange={handleChange} value={form.description} />
          </label>
          {error ? <p className="form-error">{error}</p> : null}
          <button className="primary-button" disabled={isSubmitting} type="submit">
            {isSubmitting ? 'Creating...' : 'Create draft workflow'}
          </button>
        </form>

        <section className="dashboard-panel list-panel">
          <div>
            <p className="eyebrow">Workflow model</p>
            <h2>Workflows</h2>
            <p className="muted-text">
              Use an active Post-Extraction workflow before assigning patient follow-up cases.
            </p>
          </div>
          {isLoading ? <p>Loading workflows...</p> : null}
          {!isLoading && workflows.length === 0 ? <p>No workflows yet.</p> : null}
          <ul className="resource-list">
            {workflows.map((workflow) => (
              <li key={workflow.id}>
                <span>
                  <Link to={`/admin/workflows/${workflow.id}`}>{workflow.name}</Link>
                  <small>{formatConstant(workflow.treatment_type)}</small>
                </span>
                <span className={`status-badge ${statusClass(workflow.status)}`}>
                  {formatConstant(workflow.status)}
                </span>
              </li>
            ))}
          </ul>
        </section>
      </section>
    </main>
  )
}
