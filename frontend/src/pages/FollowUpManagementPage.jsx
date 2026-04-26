import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  createFollowUpCase,
  createPatientProfile,
  listFollowUpCases,
  listPatientProfiles,
  listPatientUsers,
} from '../api/patients.js'
import { listSymptomReports } from '../api/reports.js'
import { listWorkflows } from '../api/workflows.js'
import { useAuth } from '../auth/useAuth.js'

const profileInitial = {
  allergies: '',
  dental_notes: '',
  emergency_contact: '',
  phone: '',
  user: '',
}

const caseInitial = {
  assigned_staff: '',
  notes: '',
  patient: '',
  treatment_date: '',
  workflow: '',
}

export default function FollowUpManagementPage() {
  const { logout } = useAuth()
  const [patientUsers, setPatientUsers] = useState([])
  const [profiles, setProfiles] = useState([])
  const [cases, setCases] = useState([])
  const [reports, setReports] = useState([])
  const [workflows, setWorkflows] = useState([])
  const [profileForm, setProfileForm] = useState(profileInitial)
  const [caseForm, setCaseForm] = useState(caseInitial)
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(true)

  const activeWorkflows = useMemo(
    () => workflows.filter((workflow) => workflow.status === 'ACTIVE'),
    [workflows],
  )
  const reportsByCase = useMemo(
    () =>
      reports.reduce((grouped, report) => {
        const caseReports = grouped[report.follow_up_case] || []
        return {
          ...grouped,
          [report.follow_up_case]: [...caseReports, report],
        }
      }, {}),
    [reports],
  )

  async function fetchData() {
    const [usersData, profilesData, casesData, workflowsData, reportsData] = await Promise.all([
      listPatientUsers(),
      listPatientProfiles(),
      listFollowUpCases(),
      listWorkflows(),
      listSymptomReports(),
    ])

    return {
      casesData,
      profilesData,
      reportsData,
      usersData,
      workflowsData,
    }
  }

  async function loadData() {
    const data = await fetchData()
    setPatientUsers(data.usersData)
    setProfiles(data.profilesData)
    setCases(data.casesData)
    setReports(data.reportsData)
    setWorkflows(data.workflowsData)
  }

  useEffect(() => {
    let isMounted = true

    fetchData()
      .then((data) => {
        if (!isMounted) {
          return
        }
        setPatientUsers(data.usersData)
        setProfiles(data.profilesData)
        setCases(data.casesData)
        setReports(data.reportsData)
        setWorkflows(data.workflowsData)
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

  const handleProfileChange = (event) => {
    setProfileForm((current) => ({
      ...current,
      [event.target.name]: event.target.value,
    }))
  }

  const handleCaseChange = (event) => {
    setCaseForm((current) => ({
      ...current,
      [event.target.name]: event.target.value,
    }))
  }

  const submitProfile = async (event) => {
    event.preventDefault()
    setError('')

    try {
      await createPatientProfile({
        ...profileForm,
        user: Number(profileForm.user),
      })
      setProfileForm(profileInitial)
      await loadData()
    } catch (err) {
      setError(err.message)
    }
  }

  const submitCase = async (event) => {
    event.preventDefault()
    setError('')

    try {
      await createFollowUpCase({
        ...caseForm,
        assigned_staff: caseForm.assigned_staff ? Number(caseForm.assigned_staff) : null,
        patient: Number(caseForm.patient),
        workflow: Number(caseForm.workflow),
      })
      setCaseForm(caseInitial)
      await loadData()
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <main className="app-shell">
      <header className="top-bar">
        <div>
          <p className="eyebrow">Staff area</p>
          <h1>Follow-Up Cases</h1>
        </div>
        <div className="button-row">
          <Link className="secondary-link" to="/dashboard">
            Dashboard
          </Link>
          <button className="secondary-button" type="button" onClick={logout}>
            Logout
          </button>
        </div>
      </header>

      {error ? <p className="form-error page-error">{error}</p> : null}

      <section className="split-layout">
        <div className="stacked-panels">
          <form className="panel-form" onSubmit={submitProfile}>
            <h2>Create Patient Profile</h2>
            <label>
              Patient user
              <select name="user" onChange={handleProfileChange} required value={profileForm.user}>
                <option value="">Select patient user</option>
                {patientUsers.map((user) => (
                  <option key={user.id} value={user.id}>
                    {user.username}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Phone
              <input name="phone" onChange={handleProfileChange} value={profileForm.phone} />
            </label>
            <label>
              Allergies
              <textarea
                name="allergies"
                onChange={handleProfileChange}
                value={profileForm.allergies}
              />
            </label>
            <label>
              Dental notes
              <textarea
                name="dental_notes"
                onChange={handleProfileChange}
                value={profileForm.dental_notes}
              />
            </label>
            <label>
              Emergency contact
              <input
                name="emergency_contact"
                onChange={handleProfileChange}
                value={profileForm.emergency_contact}
              />
            </label>
            <button className="primary-button" type="submit">
              Create profile
            </button>
          </form>

          <form className="panel-form" onSubmit={submitCase}>
            <h2>Create Follow-Up Case</h2>
            <label>
              Patient profile
              <select name="patient" onChange={handleCaseChange} required value={caseForm.patient}>
                <option value="">Select patient profile</option>
                {profiles.map((profile) => (
                  <option key={profile.id} value={profile.id}>
                    {profile.user_detail.username}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Active workflow
              <select name="workflow" onChange={handleCaseChange} required value={caseForm.workflow}>
                <option value="">Select active workflow</option>
                {activeWorkflows.map((workflow) => (
                  <option key={workflow.id} value={workflow.id}>
                    {workflow.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Treatment date
              <input
                name="treatment_date"
                onChange={handleCaseChange}
                required
                type="date"
                value={caseForm.treatment_date}
              />
            </label>
            <label>
              Assigned staff user id
              <input
                min="1"
                name="assigned_staff"
                onChange={handleCaseChange}
                type="number"
                value={caseForm.assigned_staff}
              />
            </label>
            <label>
              Notes
              <textarea name="notes" onChange={handleCaseChange} value={caseForm.notes} />
            </label>
            <button className="primary-button" type="submit">
              Create follow-up case
            </button>
          </form>
        </div>

        <section className="dashboard-panel list-panel">
          <div>
            <p className="eyebrow">Runtime cases</p>
            <h2>Current Follow-Up Cases</h2>
          </div>
          {isLoading ? <p>Loading cases...</p> : null}
          {!isLoading && cases.length === 0 ? <p>No follow-up cases yet.</p> : null}
          <ul className="resource-list">
            {cases.map((item) => (
              <li key={item.id}>
                <span>
                  <strong>{item.patient_detail.user_detail.username}</strong>
                  <small>{item.workflow_detail.name}</small>
                  <CaseReportList reports={reportsByCase[item.id] || []} />
                </span>
                <span>{item.status}</span>
              </li>
            ))}
          </ul>
        </section>
      </section>
    </main>
  )
}

function CaseReportList({ reports }) {
  if (reports.length === 0) {
    return <small>No symptom reports yet.</small>
  }

  return (
    <span className="nested-report-list">
      {reports.map((report) => (
        <small key={report.id}>
          Report day {report.day_after_treatment}: pain {report.pain_level}/10, swelling{' '}
          {report.swelling}, bleeding {report.bleeding}, fever {report.fever ? 'yes' : 'no'}, bad
          smell/taste {report.bad_smell ? 'yes' : 'no'}
        </small>
      ))}
    </span>
  )
}
