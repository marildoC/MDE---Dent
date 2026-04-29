import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { generateAdvice } from '../api/aiSupport.js'
import { createAppointment, listAppointments, updateAppointment } from '../api/appointments.js'
import { evaluateReport } from '../api/decisionEngine.js'
import { listEscalationCases, updateEscalationCase } from '../api/escalations.js'
import {
  createFollowUpCase,
  createPatientProfileWithUser,
  listFollowUpCases,
  listPatientProfiles,
} from '../api/patients.js'
import { listSymptomReports } from '../api/reports.js'
import { listWorkflows } from '../api/workflows.js'
import { useAuth } from '../auth/useAuth.js'
import {
  formatBoolean,
  formatConstant,
  formatDateTime,
  riskClass,
  statusClass,
} from '../utils/display.js'

const profileInitial = {
  allergies: '',
  dental_notes: '',
  email: '',
  first_name: '',
  last_name: '',
  password: '',
  phone: '',
}

const caseInitial = {
  assigned_staff: '',
  notes: '',
  patient: '',
  treatment_date: '',
  workflow: '',
}

const activeEscalationStatuses = new Set(['NEW', 'IN_REVIEW', 'WAITING_FOR_PATIENT'])
const escalationStatusLabels = {
  NEW: 'New',
  IN_REVIEW: 'In review',
  WAITING_FOR_PATIENT: 'Waiting for patient',
  APPOINTMENT_REQUIRED: 'Appointment required',
  RESOLVED: 'Resolved',
  CLOSED: 'Closed',
}
const escalationTransitions = {
  NEW: ['IN_REVIEW', 'APPOINTMENT_REQUIRED', 'RESOLVED'],
  IN_REVIEW: ['WAITING_FOR_PATIENT', 'APPOINTMENT_REQUIRED', 'RESOLVED'],
  WAITING_FOR_PATIENT: ['IN_REVIEW', 'APPOINTMENT_REQUIRED', 'RESOLVED'],
  APPOINTMENT_REQUIRED: ['RESOLVED'],
  RESOLVED: ['CLOSED'],
  CLOSED: [],
}
const appointmentStatusLabels = {
  REQUESTED: 'Requested',
  PRIORITY_SUGGESTED: 'Priority suggested',
  SCHEDULED: 'Scheduled',
  COMPLETED: 'Completed',
  CANCELLED: 'Cancelled',
}
const appointmentTransitions = {
  REQUESTED: ['SCHEDULED', 'CANCELLED'],
  PRIORITY_SUGGESTED: ['SCHEDULED', 'CANCELLED'],
  SCHEDULED: ['COMPLETED', 'CANCELLED'],
  COMPLETED: [],
  CANCELLED: [],
}
const terminalAppointmentStatuses = new Set(['COMPLETED', 'CANCELLED'])

function statusOptions(currentStatus, transitions, labels) {
  const values = [currentStatus, ...(transitions[currentStatus] || [])]
  return values.map((value) => ({ label: labels[value] || value, value }))
}

function RiskBadge({ value }) {
  return <span className={`status-badge ${riskClass(value)}`}>{formatConstant(value)}</span>
}

function patientProfileLabel(profile) {
  const firstName = profile?.user_detail?.first_name?.trim()
  const lastName = profile?.user_detail?.last_name?.trim()
  const fullName = [firstName, lastName].filter(Boolean).join(' ')
  return fullName || profile?.user_detail?.username || 'Unknown patient'
}

function patientProfileUsername(profile) {
  return profile?.user_detail?.username || 'Unavailable username'
}

function patientSearchText(profile) {
  return [
    patientProfileLabel(profile),
    patientProfileUsername(profile),
    profile?.user_detail?.email || '',
  ]
    .join(' ')
    .toLowerCase()
}

function findDuplicatePatientProfile(profiles, firstName, lastName) {
  const normalizedFirst = firstName.trim().toLowerCase()
  const normalizedLast = lastName.trim().toLowerCase()
  if (!normalizedFirst || !normalizedLast) {
    return null
  }

  return (
    profiles.find(
      (profile) =>
        profile.user_detail?.first_name?.trim().toLowerCase() === normalizedFirst &&
        profile.user_detail?.last_name?.trim().toLowerCase() === normalizedLast,
    ) || null
  )
}

function buildEscalationDrafts(escalations) {
  return escalations.reduce((drafts, escalation) => {
    return {
      ...drafts,
      [escalation.id]: {
        staff_response: escalation.staff_response || '',
        status: escalation.status,
      },
    }
  }, {})
}

function priorityForEscalation(escalation) {
  const assessmentPriority = escalation.risk_assessment_detail?.appointment_priority
  if (assessmentPriority && assessmentPriority !== 'NONE') {
    return assessmentPriority
  }
  return escalation.urgency === 'URGENT' ? 'URGENT' : 'HIGH'
}

function toDateTimeInput(value) {
  if (!value) {
    return ''
  }
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return ''
  }
  return date.toISOString().slice(0, 16)
}

function buildAppointmentDrafts(escalations, appointments) {
  const appointmentByEscalation = new Map(
    appointments.map((appointment) => [appointment.escalation_case, appointment]),
  )

  return escalations.reduce((drafts, escalation) => {
    const appointment = appointmentByEscalation.get(escalation.id)
    return {
      ...drafts,
      [escalation.id]: {
        notes: appointment?.notes || '',
        priority: appointment?.priority || priorityForEscalation(escalation),
        scheduled_at: toDateTimeInput(appointment?.scheduled_at),
        status: appointment?.status || 'PRIORITY_SUGGESTED',
      },
    }
  }, {})
}

export default function FollowUpManagementPage() {
  const { logout } = useAuth()
  const [appointments, setAppointments] = useState([])
  const [appointmentDrafts, setAppointmentDrafts] = useState({})
  const [profiles, setProfiles] = useState([])
  const [cases, setCases] = useState([])
  const [escalations, setEscalations] = useState([])
  const [escalationDrafts, setEscalationDrafts] = useState({})
  const [expandedEscalations, setExpandedEscalations] = useState({})
  const [editingEscalations, setEditingEscalations] = useState({})
  const [expandedPatients, setExpandedPatients] = useState({})
  const [expandedCases, setExpandedCases] = useState({})
  const [reports, setReports] = useState([])
  const [workflows, setWorkflows] = useState([])
  const [profileForm, setProfileForm] = useState(profileInitial)
  const [caseForm, setCaseForm] = useState(caseInitial)
  const [patientSearch, setPatientSearch] = useState('')
  const [isPatientSelectorOpen, setIsPatientSelectorOpen] = useState(false)
  const [profileMessage, setProfileMessage] = useState('')
  const [profileError, setProfileError] = useState('')
  const [error, setError] = useState('')
  const [evaluatingReportId, setEvaluatingReportId] = useState(null)
  const [generatingAdviceId, setGeneratingAdviceId] = useState(null)
  const [updatingAppointmentId, setUpdatingAppointmentId] = useState(null)
  const [updatingEscalationId, setUpdatingEscalationId] = useState(null)
  const [isCreatingProfile, setIsCreatingProfile] = useState(false)
  const [isCreatingCase, setIsCreatingCase] = useState(false)
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
  const escalationByReport = useMemo(
    () =>
      escalations.reduce((grouped, escalation) => {
        return {
          ...grouped,
          [escalation.report]: escalation,
        }
      }, {}),
    [escalations],
  )
  const appointmentByEscalation = useMemo(
    () =>
      appointments.reduce((grouped, appointment) => {
        return {
          ...grouped,
          [appointment.escalation_case]: appointment,
        }
      }, {}),
    [appointments],
  )
  const activeEscalations = useMemo(
    () => escalations.filter((escalation) => activeEscalationStatuses.has(escalation.status)),
    [escalations],
  )
  const handledEscalations = useMemo(
    () => escalations.filter((escalation) => !activeEscalationStatuses.has(escalation.status)),
    [escalations],
  )
  const patientCaseGroups = useMemo(() => groupCasesByPatient(cases), [cases])
  const duplicatePatientProfile = useMemo(
    () => findDuplicatePatientProfile(profiles, profileForm.first_name, profileForm.last_name),
    [profileForm.first_name, profileForm.last_name, profiles],
  )

  async function fetchData() {
    const requests = {
      appointmentsData: listAppointments(),
      casesData: listFollowUpCases(),
      escalationsData: listEscalationCases(),
      profilesData: listPatientProfiles(),
      reportsData: listSymptomReports(),
      workflowsData: listWorkflows(),
    }
    const results = await Promise.allSettled(Object.entries(requests).map(([, request]) => request))
    const entries = Object.keys(requests)
    const errors = []
    const data = {
      appointmentsData: [],
      casesData: [],
      escalationsData: [],
      profilesData: [],
      reportsData: [],
      workflowsData: [],
    }

    results.forEach((result, index) => {
      const key = entries[index]
      if (result.status === 'fulfilled') {
        data[key] = result.value
        return
      }

      errors.push(result.reason.message)
    })

    return {
      ...data,
      error: errors[0] || '',
    }
  }

  async function loadData() {
    const data = await fetchData()
    setAppointments(data.appointmentsData)
    setProfiles(data.profilesData)
    setCases(data.casesData)
    setEscalations(data.escalationsData)
    setEscalationDrafts(buildEscalationDrafts(data.escalationsData))
    setAppointmentDrafts(buildAppointmentDrafts(data.escalationsData, data.appointmentsData))
    setExpandedEscalations((current) => pruneExpandedMap(current, getEscalationIds(data.escalationsData)))
    setEditingEscalations((current) => pruneExpandedMap(current, getEscalationIds(data.escalationsData)))
    setExpandedPatients((current) => pruneExpandedMap(current, getPatientIds(data.casesData)))
    setExpandedCases((current) => pruneExpandedMap(current, data.casesData.map((item) => item.id)))
    setReports(data.reportsData)
    setWorkflows(data.workflowsData)
    setError(data.error)
  }

  useEffect(() => {
    let isMounted = true

    fetchData()
      .then((data) => {
        if (!isMounted) {
          return
        }
        setAppointments(data.appointmentsData)
        setProfiles(data.profilesData)
        setCases(data.casesData)
        setEscalations(data.escalationsData)
        setEscalationDrafts(buildEscalationDrafts(data.escalationsData))
        setAppointmentDrafts(buildAppointmentDrafts(data.escalationsData, data.appointmentsData))
        setExpandedEscalations((current) =>
          pruneExpandedMap(current, getEscalationIds(data.escalationsData)),
        )
        setEditingEscalations((current) =>
          pruneExpandedMap(current, getEscalationIds(data.escalationsData)),
        )
        setExpandedPatients((current) => pruneExpandedMap(current, getPatientIds(data.casesData)))
        setExpandedCases((current) =>
          pruneExpandedMap(
            current,
            data.casesData.map((item) => item.id),
          ),
        )
        setReports(data.reportsData)
        setWorkflows(data.workflowsData)
        setError(data.error)
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
    setProfileError('')
    setProfileMessage('')
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
    setProfileError('')
    setProfileMessage('')

    if (duplicatePatientProfile) {
      setProfileError('A patient with this first name and last name already exists.')
      return
    }

    setIsCreatingProfile(true)
    try {
      const profile = await createPatientProfileWithUser(profileForm)
      const createdName = patientProfileLabel(profile)
      const username = profile.user_detail?.username || 'Unavailable'
      setProfileForm(profileInitial)
      setProfileMessage(`Created patient ${createdName}. Login username: ${username}. Password was set.`)
      await loadData()
    } catch (err) {
      setProfileError(err.message)
    } finally {
      setIsCreatingProfile(false)
    }
  }

  const submitCase = async (event) => {
    event.preventDefault()
    setError('')

    if (!caseForm.patient) {
      setError('Select a patient profile before creating a follow-up case.')
      return
    }

    setIsCreatingCase(true)
    try {
      await createFollowUpCase({
        ...caseForm,
        assigned_staff: caseForm.assigned_staff ? Number(caseForm.assigned_staff) : null,
        patient: Number(caseForm.patient),
        workflow: Number(caseForm.workflow),
      })
      setCaseForm(caseInitial)
      setPatientSearch('')
      await loadData()
    } catch (err) {
      setError(err.message)
    } finally {
      setIsCreatingCase(false)
    }
  }

  const handleEvaluateReport = async (reportId) => {
    setError('')
    setEvaluatingReportId(reportId)
    try {
      await evaluateReport(reportId)
      await loadData()
    } catch (err) {
      setError(err.message)
    } finally {
      setEvaluatingReportId(null)
    }
  }

  const handleGenerateAdvice = async (assessmentId) => {
    setError('')
    setGeneratingAdviceId(assessmentId)
    try {
      await generateAdvice(assessmentId)
      await loadData()
    } catch (err) {
      setError(err.message)
    } finally {
      setGeneratingAdviceId(null)
    }
  }

  const handleEscalationDraftChange = (escalationId, field, value) => {
    setEscalationDrafts((current) => ({
      ...current,
      [escalationId]: {
        ...(current[escalationId] || {}),
        [field]: value,
      },
    }))
  }

  const handleEscalationUpdate = async (escalationId) => {
    setError('')
    setUpdatingEscalationId(escalationId)
    try {
      await updateEscalationCase(escalationId, escalationDrafts[escalationId] || {})
      await loadData()
    } catch (err) {
      setError(err.message)
    } finally {
      setUpdatingEscalationId(null)
    }
  }

  const handleAppointmentDraftChange = (escalationId, field, value) => {
    setAppointmentDrafts((current) => ({
      ...current,
      [escalationId]: {
        ...(current[escalationId] || {}),
        [field]: value,
      },
    }))
  }

  const handleAppointmentSave = async (escalationId, appointmentId) => {
    const draft = appointmentDrafts[escalationId] || {}
    const payload = {
      notes: draft.notes || '',
      priority: draft.priority,
      scheduled_at: draft.scheduled_at || null,
      status: draft.status || 'PRIORITY_SUGGESTED',
    }

    setError('')
    setUpdatingAppointmentId(appointmentId || `new-${escalationId}`)
    try {
      if (appointmentId) {
        await updateAppointment(appointmentId, payload)
      } else {
        await createAppointment({
          ...payload,
          escalation_case: escalationId,
        })
      }
      await loadData()
    } catch (err) {
      setError(err.message)
    } finally {
      setUpdatingAppointmentId(null)
    }
  }

  const toggleEscalation = (escalationId) => {
    setExpandedEscalations((current) => ({
      ...current,
      [escalationId]: !current[escalationId],
    }))
  }

  const toggleEscalationEditing = (escalationId) => {
    setExpandedEscalations((current) => ({
      ...current,
      [escalationId]: true,
    }))
    setEditingEscalations((current) => ({
      ...current,
      [escalationId]: !current[escalationId],
    }))
  }

  const togglePatient = (patientId) => {
    setExpandedPatients((current) => ({
      ...current,
      [patientId]: !current[patientId],
    }))
  }

  const toggleCase = (caseId) => {
    setExpandedCases((current) => ({
      ...current,
      [caseId]: !current[caseId],
    }))
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
            <p className="muted-text form-context">
              Create a patient login and profile before assigning an active workflow.
            </p>
            <label>
              First name
              <input
                name="first_name"
                onChange={handleProfileChange}
                required
                value={profileForm.first_name}
              />
            </label>
            <label>
              Last name
              <input
                name="last_name"
                onChange={handleProfileChange}
                required
                value={profileForm.last_name}
              />
            </label>
            {duplicatePatientProfile ? (
              <p className="form-error compact-form-error">
                A patient with this first name and last name already exists.
              </p>
            ) : null}
            <label>
              Email
              <input
                name="email"
                onChange={handleProfileChange}
                required
                type="email"
                value={profileForm.email}
              />
            </label>
            <label>
              Password
              <input
                name="password"
                onChange={handleProfileChange}
                required
                type="password"
                value={profileForm.password}
              />
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
            <button
              className="primary-button"
              disabled={isCreatingProfile || Boolean(duplicatePatientProfile)}
              type="submit"
            >
              {isCreatingProfile ? 'Creating profile...' : 'Create profile'}
            </button>
            {profileMessage ? <p className="success-message">{profileMessage}</p> : null}
            {profileError ? <p className="form-error compact-form-error">{profileError}</p> : null}
          </form>

          <form className="panel-form" onSubmit={submitCase}>
            <h2>Create Follow-Up Case</h2>
            <p className="muted-text form-context">
              Only active workflows can be assigned to patients.
            </p>
            <SearchablePatientSelector
              isOpen={isPatientSelectorOpen}
              onClearSelection={() =>
                setCaseForm((current) => ({
                  ...current,
                  patient: '',
                }))
              }
              onOpenChange={setIsPatientSelectorOpen}
              onQueryChange={setPatientSearch}
              onSelect={(profile) => {
                setCaseForm((current) => ({
                  ...current,
                  patient: String(profile.id),
                }))
                setPatientSearch(patientProfileLabel(profile))
                setIsPatientSelectorOpen(false)
              }}
              profiles={profiles}
              query={patientSearch}
              selectedProfileId={caseForm.patient}
            />
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
              {activeWorkflows.length === 0 ? (
                <small className="muted-text">No active workflows are available yet.</small>
              ) : null}
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
              Assigned staff user ID (optional)
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
            <button className="primary-button" disabled={isCreatingCase} type="submit">
              {isCreatingCase ? 'Creating case...' : 'Create follow-up case'}
            </button>
          </form>
        </div>

        <div className="operations-column">
          <EscalationQueue
            activeEscalations={activeEscalations}
            appointmentByEscalation={appointmentByEscalation}
            appointmentDrafts={appointmentDrafts}
            drafts={escalationDrafts}
            editingEscalations={editingEscalations}
            expandedEscalations={expandedEscalations}
            handledEscalations={handledEscalations}
            onAppointmentDraftChange={handleAppointmentDraftChange}
            onAppointmentSave={handleAppointmentSave}
            onDraftChange={handleEscalationDraftChange}
            onToggle={toggleEscalation}
            onToggleEdit={toggleEscalationEditing}
            onUpdate={handleEscalationUpdate}
            updatingAppointmentId={updatingAppointmentId}
            updatingEscalationId={updatingEscalationId}
          />

          <section className="dashboard-panel list-panel">
            <div>
              <p className="eyebrow">Runtime cases</p>
              <h2>Runtime Follow-Up Cases</h2>
              <p className="muted-text">
                Patients are grouped first; expand a patient to review their follow-up cases,
                reports, deterministic assessments, advice, escalation, and appointments.
              </p>
            </div>
            {isLoading ? <p>Loading cases...</p> : null}
            {!isLoading && cases.length === 0 ? <p>No follow-up cases yet.</p> : null}
            <ul className="resource-list accordion-list patient-case-list">
              {patientCaseGroups.map((group) => (
                <PatientCaseGroup
                  appointmentByEscalation={appointmentByEscalation}
                  escalationByReport={escalationByReport}
                  evaluatingReportId={evaluatingReportId}
                  expandedCases={expandedCases}
                  generatingAdviceId={generatingAdviceId}
                  group={group}
                  isExpanded={Boolean(expandedPatients[group.patientId])}
                  key={group.patientId}
                  onEvaluate={handleEvaluateReport}
                  onGenerateAdvice={handleGenerateAdvice}
                  onToggle={() => togglePatient(group.patientId)}
                  onToggleCase={toggleCase}
                  reportsByCase={reportsByCase}
                />
              ))}
            </ul>
          </section>
        </div>
      </section>
    </main>
  )
}

function pruneExpandedMap(current, ids) {
  const availableIds = new Set(ids.map((id) => String(id)))
  return Object.fromEntries(
    Object.entries(current).filter(([itemId]) => availableIds.has(itemId)),
  )
}

function getEscalationIds(escalations) {
  return escalations.map((escalation) => escalation.id)
}

function patientKeyForCase(item) {
  return item.patient || item.patient_detail?.id || `case-${item.id}`
}

function getPatientIds(casesData) {
  return Array.from(new Set(casesData.map((item) => patientKeyForCase(item))))
}

function groupCasesByPatient(casesData) {
  const grouped = new Map()

  casesData.forEach((item) => {
    const patientId = patientKeyForCase(item)
    const existing = grouped.get(patientId) || {
      cases: [],
      patientDetail: item.patient_detail,
      patientId,
    }

    existing.cases.push(item)
    grouped.set(patientId, existing)
  })

  return Array.from(grouped.values()).sort((left, right) =>
    patientName(left.patientDetail).localeCompare(patientName(right.patientDetail)),
  )
}

function patientName(patientDetail) {
  return patientProfileLabel(patientDetail)
}

function SearchablePatientSelector({
  isOpen,
  onClearSelection,
  onOpenChange,
  onQueryChange,
  onSelect,
  profiles,
  query,
  selectedProfileId,
}) {
  const selectedProfile = profiles.find((profile) => String(profile.id) === String(selectedProfileId))
  const normalizedQuery = query.trim().toLowerCase()
  const matchingProfiles = normalizedQuery
    ? profiles.filter((profile) => patientSearchText(profile).includes(normalizedQuery))
    : profiles
  const visibleProfiles = matchingProfiles.slice(0, 10)

  const handleInputChange = (event) => {
    onQueryChange(event.target.value)
    onClearSelection()
    onOpenChange(true)
  }

  const handleKeyDown = (event) => {
    if (event.key === 'Escape') {
      onOpenChange(false)
      return
    }
    if (event.key === 'Enter' && isOpen && visibleProfiles.length > 0) {
      event.preventDefault()
      onSelect(visibleProfiles[0])
    }
  }

  return (
    <div
      className="panel-field searchable-select-field"
      onBlur={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget)) {
          onOpenChange(false)
        }
      }}
    >
      <label htmlFor="follow-up-patient-search">Patient profile</label>
      <div className="searchable-select">
        <input
          autoComplete="off"
          id="follow-up-patient-search"
          onChange={handleInputChange}
          onFocus={() => onOpenChange(true)}
          onKeyDown={handleKeyDown}
          placeholder="Search patient by name or username"
          role="combobox"
          value={query}
        />
        {selectedProfile ? (
          <small className="selected-patient-meta">
            Selected: {patientProfileLabel(selectedProfile)} | username:{' '}
            {patientProfileUsername(selectedProfile)}
          </small>
        ) : null}
        {isOpen ? (
          <div className="searchable-select-menu" role="listbox">
            {visibleProfiles.length === 0 ? (
              <p className="muted-text">No matching patient profiles.</p>
            ) : (
              <>
                {visibleProfiles.map((profile) => (
                  <button
                    className={`searchable-select-option${
                      String(profile.id) === String(selectedProfileId) ? ' is-selected' : ''
                    }`}
                    key={profile.id}
                    onClick={() => onSelect(profile)}
                    role="option"
                    type="button"
                  >
                    <span>{patientProfileLabel(profile)}</span>
                    <small>username: {patientProfileUsername(profile)}</small>
                  </button>
                ))}
                {matchingProfiles.length > visibleProfiles.length ? (
                  <small className="muted-text">
                    Showing first {visibleProfiles.length} of {matchingProfiles.length} matches.
                  </small>
                ) : null}
              </>
            )}
          </div>
        ) : null}
      </div>
    </div>
  )
}

function latestReport(reports) {
  return reports[reports.length - 1] || null
}

function PatientCaseGroup({
  appointmentByEscalation,
  escalationByReport,
  evaluatingReportId,
  expandedCases,
  generatingAdviceId,
  group,
  isExpanded,
  onEvaluate,
  onGenerateAdvice,
  onToggle,
  onToggleCase,
  reportsByCase,
}) {
  const caseCount = group.cases.length
  const reportCount = group.cases.reduce(
    (total, item) => total + (reportsByCase[item.id]?.length || 0),
    0,
  )
  const activeCaseCount = group.cases.filter((item) => !['RESOLVED', 'CLOSED'].includes(item.status))
    .length

  return (
    <li className={`accordion-item patient-item${isExpanded ? ' is-expanded' : ''}`}>
      <button className="accordion-trigger" onClick={onToggle} type="button">
        <span>
          <strong>{patientName(group.patientDetail)}</strong>
          <small>
            {caseCount} follow-up {caseCount === 1 ? 'case' : 'cases'} | {reportCount} symptom{' '}
            {reportCount === 1 ? 'report' : 'reports'} | {activeCaseCount} active
          </small>
        </span>
        <span className="chevron" aria-hidden="true">
          {isExpanded ? '-' : '+'}
        </span>
      </button>

      {isExpanded ? (
        <div className="accordion-body patient-case-body">
          <ul className="resource-list accordion-list case-accordion-list">
            {group.cases.map((item) => (
              <FollowUpCaseItem
                appointmentByEscalation={appointmentByEscalation}
                caseItem={item}
                escalationByReport={escalationByReport}
                evaluatingReportId={evaluatingReportId}
                generatingAdviceId={generatingAdviceId}
                isExpanded={Boolean(expandedCases[item.id])}
                key={item.id}
                onEvaluate={onEvaluate}
                onGenerateAdvice={onGenerateAdvice}
                onToggle={() => onToggleCase(item.id)}
                reports={reportsByCase[item.id] || []}
              />
            ))}
          </ul>
        </div>
      ) : null}
    </li>
  )
}

function FollowUpCaseItem({
  appointmentByEscalation,
  caseItem,
  escalationByReport,
  evaluatingReportId,
  generatingAdviceId,
  isExpanded,
  onEvaluate,
  onGenerateAdvice,
  onToggle,
  reports,
}) {
  const latest = latestReport(reports)

  return (
    <li className={`accordion-item case-item${isExpanded ? ' is-expanded' : ''}`}>
      <button className="accordion-trigger case-trigger" onClick={onToggle} type="button">
        <span>
          <strong>{caseItem.workflow_detail.name}</strong>
          <small>
            Treatment date: {caseItem.treatment_date} | Staff:{' '}
            {caseItem.assigned_staff_detail?.username || 'Unassigned'}
          </small>
          <small>
            Reports: {reports.length}
            {latest?.risk_assessment ? (
              <>
                {' '}
                | Latest risk: <RiskBadge value={latest.risk_assessment.risk_level} />
              </>
            ) : null}
          </small>
        </span>
        <span className="case-trigger-actions">
          <span className={`status-badge ${statusClass(caseItem.status)}`}>
            {formatConstant(caseItem.status)}
          </span>
          <span className="chevron" aria-hidden="true">
            {isExpanded ? '-' : '+'}
          </span>
        </span>
      </button>

      {isExpanded ? (
        <div className="accordion-body case-detail-body">
          <CaseReportList
            appointmentByEscalation={appointmentByEscalation}
            escalationByReport={escalationByReport}
            evaluatingReportId={evaluatingReportId}
            generatingAdviceId={generatingAdviceId}
            onEvaluate={onEvaluate}
            onGenerateAdvice={onGenerateAdvice}
            reports={reports}
          />
        </div>
      ) : null}
    </li>
  )
}

function CaseReportList({
  appointmentByEscalation,
  escalationByReport,
  evaluatingReportId,
  generatingAdviceId,
  onEvaluate,
  onGenerateAdvice,
  reports,
}) {
  if (reports.length === 0) {
    return <small>No symptom reports yet.</small>
  }

  return (
    <span className="nested-report-list">
      {reports.map((report) => (
        <span className="report-summary-item" key={report.id}>
          <small>
            Report day {report.day_after_treatment}: pain {report.pain_level}/10, swelling{' '}
            {formatConstant(report.swelling)}, bleeding {formatConstant(report.bleeding)}, fever{' '}
            {formatBoolean(report.fever)}, bad smell/taste {formatBoolean(report.bad_smell)}
          </small>
          <RiskAssessmentSummary
            assessment={report.risk_assessment}
            appointment={
              escalationByReport[report.id]
                ? appointmentByEscalation[escalationByReport[report.id].id]
                : null
            }
            escalation={escalationByReport[report.id]}
            evaluating={evaluatingReportId === report.id}
            generatingAdvice={generatingAdviceId === report.risk_assessment?.id}
            onEvaluate={() => onEvaluate(report.id)}
            onGenerateAdvice={() => onGenerateAdvice(report.risk_assessment.id)}
          />
        </span>
      ))}
    </span>
  )
}

function RiskAssessmentSummary({
  assessment,
  appointment,
  escalation,
  evaluating,
  generatingAdvice,
  onEvaluate,
  onGenerateAdvice,
}) {
  if (!assessment) {
    return (
      <span className="assessment-summary">
        <small>No risk assessment yet.</small>
        <button
          className="secondary-button compact-button"
          disabled={evaluating}
          onClick={onEvaluate}
          type="button"
        >
          {evaluating ? 'Evaluating...' : 'Evaluate'}
        </button>
      </span>
    )
  }

  return (
    <span className="assessment-summary">
      <small>
        Risk assessment: <RiskBadge value={assessment.risk_level} /> Recommended action:{' '}
        {formatConstant(assessment.recommended_action)} | Appointment priority:{' '}
        {formatConstant(assessment.appointment_priority)}
      </small>
      <small>Detected stage: {assessment.detected_stage_name || 'Unavailable'}</small>
      <small>Explanation: {assessment.explanation}</small>
      <AdviceSummary
        advice={assessment.advice_message}
        generating={generatingAdvice}
        onGenerate={onGenerateAdvice}
      />
      <EscalationSummary appointment={appointment} escalation={escalation} />
      {assessment.matched_rules.length > 0 ? (
        <small>
          Matched rules: {assessment.matched_rules.map((rule) => rule.name).join(', ')}
        </small>
      ) : null}
    </span>
  )
}

function EscalationSummary({ appointment, escalation }) {
  if (!escalation) {
    return null
  }

  return (
    <span className="escalation-summary">
      <small className="escalation-label">Staff review</small>
      <small>
        Status: {formatConstant(escalation.status)} | Urgency: {formatConstant(escalation.urgency)}
      </small>
      {escalation.staff_response ? <small>Response: {escalation.staff_response}</small> : null}
      {appointment ? <AppointmentSummary appointment={appointment} /> : null}
    </span>
  )
}

function AppointmentSummary({ appointment }) {
  return (
    <span className="appointment-summary">
      <small className="appointment-label">Appointment</small>
      <small>
        Priority: {formatConstant(appointment.priority)} | Status: {formatConstant(appointment.status)}
      </small>
      {appointment.scheduled_at ? <small>Scheduled: {formatDateTime(appointment.scheduled_at)}</small> : null}
      {appointment.notes ? <small>Notes: {appointment.notes}</small> : null}
    </span>
  )
}

function EscalationQueue({
  activeEscalations,
  appointmentByEscalation,
  appointmentDrafts,
  drafts,
  editingEscalations,
  expandedEscalations,
  handledEscalations,
  onAppointmentDraftChange,
  onAppointmentSave,
  onDraftChange,
  onToggle,
  onToggleEdit,
  onUpdate,
  updatingAppointmentId,
  updatingEscalationId,
}) {
  return (
    <section className="dashboard-panel list-panel escalation-queue">
      <div>
        <p className="eyebrow">Staff review</p>
        <h2>Escalation Queue</h2>
        <p className="muted-text">
          Urgent staff actions are listed first. Expand an item to inspect details, then use Edit
          review when staff action is needed.
        </p>
      </div>

      <section className="escalation-group">
        <h3>Active</h3>
        {activeEscalations.length === 0 ? (
          <p className="muted-text">No active escalation items need attention.</p>
        ) : null}
        <ul className="resource-list accordion-list escalation-list">
          {activeEscalations.map((escalation) => (
            <EscalationReviewCard
              appointment={appointmentByEscalation[escalation.id]}
              appointmentDraft={appointmentDrafts[escalation.id] || {}}
              draft={drafts[escalation.id] || {}}
              escalation={escalation}
              isEditing={Boolean(editingEscalations[escalation.id])}
              isExpanded={Boolean(expandedEscalations[escalation.id])}
              isSaving={updatingEscalationId === escalation.id}
              key={escalation.id}
              onAppointmentDraftChange={onAppointmentDraftChange}
              onAppointmentSave={onAppointmentSave}
              onDraftChange={onDraftChange}
              onToggle={() => onToggle(escalation.id)}
              onToggleEdit={() => onToggleEdit(escalation.id)}
              onUpdate={onUpdate}
              updatingAppointmentId={updatingAppointmentId}
            />
          ))}
        </ul>
      </section>

      <section className="escalation-group handled-escalations">
        <h3>Handled / Reviewed</h3>
        {handledEscalations.length === 0 ? (
          <p className="muted-text">No reviewed escalations yet.</p>
        ) : null}
        <ul className="resource-list accordion-list escalation-list handled-list">
          {handledEscalations.map((escalation) => (
            <EscalationReviewCard
              appointment={appointmentByEscalation[escalation.id]}
              appointmentDraft={appointmentDrafts[escalation.id] || {}}
              draft={drafts[escalation.id] || {}}
              escalation={escalation}
              isEditing={Boolean(editingEscalations[escalation.id])}
              isExpanded={Boolean(expandedEscalations[escalation.id])}
              isSaving={updatingEscalationId === escalation.id}
              key={escalation.id}
              onAppointmentDraftChange={onAppointmentDraftChange}
              onAppointmentSave={onAppointmentSave}
              onDraftChange={onDraftChange}
              onToggle={() => onToggle(escalation.id)}
              onToggleEdit={() => onToggleEdit(escalation.id)}
              onUpdate={onUpdate}
              updatingAppointmentId={updatingAppointmentId}
            />
          ))}
        </ul>
      </section>
    </section>
  )
}

function EscalationReviewCard({
  appointment,
  appointmentDraft,
  draft,
  escalation,
  isEditing,
  isExpanded,
  isSaving,
  onAppointmentDraftChange,
  onAppointmentSave,
  onDraftChange,
  onToggle,
  onToggleEdit,
  onUpdate,
  updatingAppointmentId,
}) {
  const report = escalation.report_detail || {}
  const patient = escalation.patient_detail?.user_detail?.username || 'Unknown patient'
  const workflow = escalation.follow_up_case_detail?.workflow_detail?.name || 'Unknown workflow'
  const escalationOptions = statusOptions(
    escalation.status,
    escalationTransitions,
    escalationStatusLabels,
  )
  const isClosed = escalation.status === 'CLOSED'

  return (
    <li className={`accordion-item escalation-card${isExpanded ? ' is-expanded' : ''}`}>
      <button className="accordion-trigger escalation-trigger" onClick={onToggle} type="button">
        <span>
          <strong>
            {patient} - {formatConstant(escalation.urgency)}
          </strong>
          <small>{workflow}</small>
          <small>
            Report day {report.day_after_treatment}: pain {report.pain_level}/10, swelling{' '}
            {formatConstant(report.swelling)}, fever {formatBoolean(report.fever)}
          </small>
        </span>
        <span className="case-trigger-actions">
          <span className={`status-badge ${statusClass(escalation.status)}`}>
            {formatConstant(escalation.status)}
          </span>
          <span className="chevron" aria-hidden="true">
            {isExpanded ? '-' : '+'}
          </span>
        </span>
      </button>

      {isExpanded ? (
        <div className="accordion-body escalation-detail-body">
          <div className="escalation-detail-summary">
            <small>
              Report details: bleeding {formatConstant(report.bleeding)}, bad smell/taste{' '}
              {formatBoolean(report.bad_smell)}
            </small>
            <small>
              Risk action: {formatConstant(escalation.risk_assessment_detail?.recommended_action)}
            </small>
            {escalation.staff_response ? (
              <small>Current response: {escalation.staff_response}</small>
            ) : (
              <small>No staff response recorded yet.</small>
            )}
            {escalation.advice_message ? (
              <small>Bounded advice: {escalation.advice_message.message}</small>
            ) : null}
            {appointment ? <AppointmentSummary appointment={appointment} /> : null}
          </div>

          <div className="button-row review-actions">
            <button
              className="secondary-button compact-button"
              disabled={isClosed}
              onClick={onToggleEdit}
              type="button"
            >
              {isEditing ? 'Close editor' : 'Edit review'}
            </button>
          </div>

          {isEditing ? (
            <>
              <AppointmentControls
                appointment={appointment}
                draft={appointmentDraft}
                escalation={escalation}
                isSaving={
                  updatingAppointmentId === appointment?.id ||
                  updatingAppointmentId === `new-${escalation.id}`
                }
                onDraftChange={onAppointmentDraftChange}
                onSave={onAppointmentSave}
              />
              <div className="escalation-controls">
                <label>
                  Status
                  <select
                    disabled={isClosed}
                    onChange={(event) => onDraftChange(escalation.id, 'status', event.target.value)}
                    value={draft.status || escalation.status}
                  >
                    {escalationOptions.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Staff response
                  <textarea
                    disabled={isClosed}
                    onChange={(event) =>
                      onDraftChange(escalation.id, 'staff_response', event.target.value)
                    }
                    value={draft.staff_response || ''}
                  />
                </label>
                <div className="button-row review-actions">
                  <button
                    className="primary-button compact-button"
                    disabled={isSaving || isClosed}
                    onClick={() => onUpdate(escalation.id)}
                    type="button"
                  >
                    {isSaving ? 'Saving...' : 'Save review'}
                  </button>
                </div>
              </div>
            </>
          ) : null}
        </div>
      ) : null}
    </li>
  )
}

function AppointmentControls({ appointment, draft, escalation, isSaving, onDraftChange, onSave }) {
  const currentStatus = appointment?.status || 'PRIORITY_SUGGESTED'
  const appointmentOptions = appointment
    ? statusOptions(currentStatus, appointmentTransitions, appointmentStatusLabels)
    : [{ label: appointmentStatusLabels.PRIORITY_SUGGESTED, value: 'PRIORITY_SUGGESTED' }]
  const isTerminal = appointment && terminalAppointmentStatuses.has(appointment.status)

  return (
    <div className="appointment-controls">
      <small className="appointment-label">
        {appointment ? 'Appointment' : 'Create appointment'}
      </small>
      {appointment ? <AppointmentSummary appointment={appointment} /> : null}
      <div className="inline-fields">
        <label>
          Priority
          <select
            disabled={isTerminal}
            onChange={(event) => onDraftChange(escalation.id, 'priority', event.target.value)}
            value={draft.priority || priorityForEscalation(escalation)}
          >
            <option value="LOW">Low</option>
            <option value="NORMAL">Normal</option>
            <option value="HIGH">High</option>
            <option value="URGENT">Urgent</option>
          </select>
        </label>
        <label>
          Status
          <select
            disabled={isTerminal}
            onChange={(event) => onDraftChange(escalation.id, 'status', event.target.value)}
            value={draft.status || currentStatus}
          >
            {appointmentOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
      </div>
      <label>
        Scheduled date/time
        <input
          disabled={isTerminal}
          onChange={(event) => onDraftChange(escalation.id, 'scheduled_at', event.target.value)}
          type="datetime-local"
          value={draft.scheduled_at || ''}
        />
      </label>
      <label>
        Appointment notes
        <textarea
          disabled={isTerminal}
          onChange={(event) => onDraftChange(escalation.id, 'notes', event.target.value)}
          value={draft.notes || ''}
        />
      </label>
      <button
        className="primary-button compact-button"
        disabled={isSaving || isTerminal}
        onClick={() => onSave(escalation.id, appointment?.id)}
        type="button"
      >
        {isSaving
          ? 'Saving appointment...'
          : appointment
          ? 'Save appointment'
          : 'Create appointment'}
      </button>
    </div>
  )
}

function AdviceSummary({ advice, generating, onGenerate }) {
  if (advice) {
    return (
      <span className="advice-summary">
        <small className="advice-label">Patient guidance</small>
        <small>{advice.message}</small>
      </span>
    )
  }

  return (
    <span className="advice-summary">
      <small>No bounded advice yet.</small>
      <button
        className="secondary-button compact-button"
        disabled={generating}
        onClick={onGenerate}
        type="button"
      >
        {generating ? 'Generating...' : 'Generate advice'}
      </button>
    </span>
  )
}
