import { Link } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { getMyActiveCase } from '../api/patients.js'
import { createSymptomReport, listSymptomReports } from '../api/reports.js'
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

const reportInitial = {
  bad_smell: 'false',
  bleeding: 'NONE',
  fever: 'false',
  image: null,
  notes: '',
  pain_level: '0',
  swelling: 'NONE',
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
          {variant === 'admin' ? (
            <div className="button-row dashboard-actions">
              <Link className="primary-link" to="/admin/workflows">
                Workflow management
              </Link>
              <Link className="secondary-link" to="/follow-up-cases">
                Follow-up cases
              </Link>
            </div>
          ) : null}
          {variant === 'staff' ? (
            <Link className="primary-link" to="/follow-up-cases">
              Follow-up cases
            </Link>
          ) : null}
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
  const { logout, user } = useAuth()
  const [activeCase, setActiveCase] = useState(null)
  const [reports, setReports] = useState([])
  const [reportForm, setReportForm] = useState(reportInitial)
  const [reportFormKey, setReportFormKey] = useState(0)
  const [isLoading, setIsLoading] = useState(true)
  const [isSubmittingReport, setIsSubmittingReport] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  useEffect(() => {
    let isMounted = true

    getMyActiveCase()
      .then(async (data) => {
        if (isMounted) {
          setActiveCase(data)
        }
        if (data) {
          const reportsData = await listSymptomReports({ followUpCaseId: data.id })
          if (isMounted) {
            setReports(reportsData)
          }
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

  const loadReports = async (caseId) => {
    const reportsData = await listSymptomReports({ followUpCaseId: caseId })
    setReports(reportsData)
  }

  const handleReportChange = (event) => {
    const { files, name, value } = event.target
    setReportForm((current) => ({
      ...current,
      [name]: files ? files[0] || null : value,
    }))
  }

  const submitReport = async (event) => {
    event.preventDefault()
    if (!activeCase) {
      return
    }

    setError('')
    setMessage('')
    setIsSubmittingReport(true)

    try {
      await createSymptomReport({
        ...reportForm,
        bad_smell: reportForm.bad_smell === 'true',
        fever: reportForm.fever === 'true',
        follow_up_case: activeCase.id,
        pain_level: Number(reportForm.pain_level),
      })
      setReportForm(reportInitial)
      setReportFormKey((current) => current + 1)
      setMessage('Report submitted.')
      await loadReports(activeCase.id)
    } catch (err) {
      setError(err.message)
    } finally {
      setIsSubmittingReport(false)
    }
  }

  return (
    <main className="app-shell">
      <header className="top-bar">
        <div>
          <p className="eyebrow">DentCare-MDE</p>
          <h1>Patient Dashboard</h1>
        </div>
        <button className="secondary-button" type="button" onClick={logout}>
          Logout
        </button>
      </header>

      <section className="dashboard-panel">
        <div>
          <p className="eyebrow">Patient area</p>
          {isLoading ? <h2>Loading follow-up case...</h2> : null}
          {!isLoading && !activeCase ? <h2>No active follow-up case yet.</h2> : null}
          {activeCase ? <ActiveCaseSummary activeCase={activeCase} /> : null}
          {activeCase ? (
            <SymptomReportSection
              form={reportForm}
              formKey={reportFormKey}
              isSubmitting={isSubmittingReport}
              message={message}
              onChange={handleReportChange}
              onSubmit={submitReport}
              reports={reports}
            />
          ) : null}
          {error ? <p className="form-error">{error}</p> : null}
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

export function StaffDashboard() {
  return <DashboardLayout variant="staff" />
}

export function AdminDashboard() {
  return <DashboardLayout variant="admin" />
}

function ActiveCaseSummary({ activeCase }) {
  const workflow = activeCase.workflow_detail || {}
  const treatmentDateValue = activeCase.treatment_date || ''
  const treatmentDate = new Date(`${treatmentDateValue}T00:00:00`)
  const today = new Date()
  const hasValidTreatmentDate = !Number.isNaN(treatmentDate.getTime())
  const dayAfterTreatment = hasValidTreatmentDate
    ? Math.max(
        0,
        Math.floor((today.setHours(0, 0, 0, 0) - treatmentDate.getTime()) / 86400000),
      )
    : 'Unavailable'

  return (
    <div className="case-summary">
      <h2>{workflow.name || 'Assigned workflow unavailable'}</h2>
      <dl className="identity-list case-list">
        <div>
          <dt>Treatment type</dt>
          <dd>{workflow.treatment_type || 'Unavailable'}</dd>
        </div>
        <div>
          <dt>Treatment date</dt>
          <dd>{treatmentDateValue || 'Unavailable'}</dd>
        </div>
        <div>
          <dt>Day after treatment</dt>
          <dd>{dayAfterTreatment}</dd>
        </div>
        <div>
          <dt>Status</dt>
          <dd>{activeCase.status}</dd>
        </div>
      </dl>
    </div>
  )
}

function SymptomReportSection({
  form,
  formKey,
  isSubmitting,
  message,
  onChange,
  onSubmit,
  reports,
}) {
  return (
    <div className="report-section">
      <form className="compact-form report-form" key={formKey} onSubmit={onSubmit}>
        <h3>Submit symptom report</h3>
        <div className="inline-fields">
          <label>
            Pain level
            <input
              max="10"
              min="0"
              name="pain_level"
              onChange={onChange}
              required
              type="number"
              value={form.pain_level}
            />
          </label>
          <label>
            Swelling
            <select name="swelling" onChange={onChange} required value={form.swelling}>
              <option value="NONE">None</option>
              <option value="MILD">Mild</option>
              <option value="SEVERE">Severe</option>
            </select>
          </label>
        </div>
        <div className="inline-fields">
          <label>
            Bleeding
            <select name="bleeding" onChange={onChange} required value={form.bleeding}>
              <option value="NONE">None</option>
              <option value="MILD">Mild</option>
              <option value="SEVERE">Severe</option>
            </select>
          </label>
          <label>
            Fever
            <select name="fever" onChange={onChange} required value={form.fever}>
              <option value="false">No</option>
              <option value="true">Yes</option>
            </select>
          </label>
        </div>
        <label>
          Bad smell or taste
          <select name="bad_smell" onChange={onChange} required value={form.bad_smell}>
            <option value="false">No</option>
            <option value="true">Yes</option>
          </select>
        </label>
        <label>
          Notes
          <textarea name="notes" onChange={onChange} value={form.notes} />
        </label>
        <label>
          Image evidence
          <input name="image" onChange={onChange} type="file" />
        </label>
        <button className="primary-button" disabled={isSubmitting} type="submit">
          {isSubmitting ? 'Submitting...' : 'Submit report'}
        </button>
        {message ? <p className="success-message">{message}</p> : null}
      </form>

      <ReportHistory reports={reports} />
    </div>
  )
}

function ReportHistory({ reports }) {
  return (
    <div className="report-history">
      <h3>Report history</h3>
      {reports.length === 0 ? <p className="muted-text">No symptom reports yet.</p> : null}
      <ul className="resource-list compact-list">
        {reports.map((report) => (
          <li key={report.id}>
            <span>
              <strong>Day {report.day_after_treatment}</strong>
              <small>
                Pain {report.pain_level}/10 | Swelling {report.swelling} | Bleeding{' '}
                {report.bleeding}
              </small>
              <small>
                Fever {report.fever ? 'yes' : 'no'} | Bad smell/taste{' '}
                {report.bad_smell ? 'yes' : 'no'}
              </small>
              {report.notes ? <small>{report.notes}</small> : null}
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}
