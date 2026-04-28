import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { generateAdvice } from '../api/aiSupport.js'
import { createAppointment, listAppointments, updateAppointment } from '../api/appointments.js'
import { evaluateReport } from '../api/decisionEngine.js'
import { listEscalationCases, updateEscalationCase } from '../api/escalations.js'
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
  const [patientUsers, setPatientUsers] = useState([])
  const [profiles, setProfiles] = useState([])
  const [cases, setCases] = useState([])
  const [escalations, setEscalations] = useState([])
  const [escalationDrafts, setEscalationDrafts] = useState({})
  const [expandedHandledEscalations, setExpandedHandledEscalations] = useState({})
  const [reports, setReports] = useState([])
  const [workflows, setWorkflows] = useState([])
  const [profileForm, setProfileForm] = useState(profileInitial)
  const [caseForm, setCaseForm] = useState(caseInitial)
  const [error, setError] = useState('')
  const [evaluatingReportId, setEvaluatingReportId] = useState(null)
  const [generatingAdviceId, setGeneratingAdviceId] = useState(null)
  const [updatingAppointmentId, setUpdatingAppointmentId] = useState(null)
  const [updatingEscalationId, setUpdatingEscalationId] = useState(null)
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

  async function fetchData() {
    const requests = {
      appointmentsData: listAppointments(),
      casesData: listFollowUpCases(),
      escalationsData: listEscalationCases(),
      profilesData: listPatientProfiles(),
      reportsData: listSymptomReports(),
      usersData: listPatientUsers(),
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
      usersData: [],
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
    setPatientUsers(data.usersData)
    setAppointments(data.appointmentsData)
    setProfiles(data.profilesData)
    setCases(data.casesData)
    setEscalations(data.escalationsData)
    setEscalationDrafts(buildEscalationDrafts(data.escalationsData))
    setAppointmentDrafts(buildAppointmentDrafts(data.escalationsData, data.appointmentsData))
    setExpandedHandledEscalations((current) => pruneExpandedEscalations(current, data.escalationsData))
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
        setPatientUsers(data.usersData)
        setProfiles(data.profilesData)
        setCases(data.casesData)
        setEscalations(data.escalationsData)
        setEscalationDrafts(buildEscalationDrafts(data.escalationsData))
        setAppointmentDrafts(buildAppointmentDrafts(data.escalationsData, data.appointmentsData))
        setExpandedHandledEscalations((current) =>
          pruneExpandedEscalations(current, data.escalationsData),
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

  const toggleHandledEscalation = (escalationId) => {
    setExpandedHandledEscalations((current) => ({
      ...current,
      [escalationId]: !current[escalationId],
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
              Create a minimal patient profile before assigning an active workflow.
            </p>
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
            <p className="muted-text form-context">
              Only active workflows can be assigned to patients.
            </p>
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
            <button className="primary-button" type="submit">
              Create follow-up case
            </button>
          </form>
        </div>

        <section className="dashboard-panel list-panel">
          <div>
            <p className="eyebrow">Runtime cases</p>
            <h2>Current Follow-Up Cases</h2>
            <p className="muted-text">
              Review reports, deterministic assessments, staff review, and appointment handling
              from one place.
            </p>
          </div>
          {isLoading ? <p>Loading cases...</p> : null}
          {!isLoading && cases.length === 0 ? <p>No follow-up cases yet.</p> : null}
          <ul className="resource-list">
            {cases.map((item) => (
              <li key={item.id}>
                <span>
                  <strong>{item.patient_detail.user_detail.username}</strong>
                  <small>{item.workflow_detail.name}</small>
                  <small>
                    Treatment date: {item.treatment_date} | Staff:{' '}
                    {item.assigned_staff_detail?.username || 'Unassigned'}
                  </small>
                  <CaseReportList
                    appointmentByEscalation={appointmentByEscalation}
                    escalationByReport={escalationByReport}
                    evaluatingReportId={evaluatingReportId}
                    generatingAdviceId={generatingAdviceId}
                    onEvaluate={handleEvaluateReport}
                    onGenerateAdvice={handleGenerateAdvice}
                    reports={reportsByCase[item.id] || []}
                  />
                </span>
                <span className={`status-badge ${statusClass(item.status)}`}>
                  {formatConstant(item.status)}
                </span>
              </li>
            ))}
          </ul>

          <EscalationQueue
            activeEscalations={activeEscalations}
            appointmentByEscalation={appointmentByEscalation}
            appointmentDrafts={appointmentDrafts}
            drafts={escalationDrafts}
            expandedHandledEscalations={expandedHandledEscalations}
            handledEscalations={handledEscalations}
            onAppointmentDraftChange={handleAppointmentDraftChange}
            onAppointmentSave={handleAppointmentSave}
            onDraftChange={handleEscalationDraftChange}
            onToggleHandled={toggleHandledEscalation}
            onUpdate={handleEscalationUpdate}
            updatingAppointmentId={updatingAppointmentId}
            updatingEscalationId={updatingEscalationId}
          />
        </section>
      </section>
    </main>
  )
}

function pruneExpandedEscalations(current, escalations) {
  const availableIds = new Set(escalations.map((escalation) => String(escalation.id)))
  return Object.fromEntries(
    Object.entries(current).filter(([escalationId]) => availableIds.has(escalationId)),
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
  expandedHandledEscalations,
  handledEscalations,
  onAppointmentDraftChange,
  onAppointmentSave,
  onDraftChange,
  onToggleHandled,
  onUpdate,
  updatingAppointmentId,
  updatingEscalationId,
}) {
  return (
    <section className="escalation-queue">
      <div>
        <p className="eyebrow">Staff review</p>
        <h2>Active Escalation Queue</h2>
      </div>
      {activeEscalations.length === 0 ? (
        <p className="muted-text">No active escalation items need attention.</p>
      ) : null}
      <ul className="resource-list">
        {activeEscalations.map((escalation) => (
          <EscalationReviewCard
            appointment={appointmentByEscalation[escalation.id]}
            appointmentDraft={appointmentDrafts[escalation.id] || {}}
            draft={drafts[escalation.id] || {}}
            escalation={escalation}
            isSaving={updatingEscalationId === escalation.id}
            key={escalation.id}
            onAppointmentDraftChange={onAppointmentDraftChange}
            onAppointmentSave={onAppointmentSave}
            onDraftChange={onDraftChange}
            onUpdate={onUpdate}
            updatingAppointmentId={updatingAppointmentId}
          />
        ))}
      </ul>

      <section className="handled-escalations">
        <div>
          <p className="eyebrow">Reviewed / handled</p>
          <h3>Handled Escalations</h3>
        </div>
        {handledEscalations.length === 0 ? (
          <p className="muted-text">No reviewed escalations yet.</p>
        ) : null}
        <ul className="resource-list handled-list">
          {handledEscalations.map((escalation) => {
            const isExpanded = Boolean(expandedHandledEscalations[escalation.id])
            return (
              <EscalationReviewCard
                appointment={appointmentByEscalation[escalation.id]}
                appointmentDraft={appointmentDrafts[escalation.id] || {}}
                compact={!isExpanded}
                draft={drafts[escalation.id] || {}}
                escalation={escalation}
                isSaving={updatingEscalationId === escalation.id}
                key={escalation.id}
                onAppointmentDraftChange={onAppointmentDraftChange}
                onAppointmentSave={onAppointmentSave}
                onDraftChange={onDraftChange}
                onToggle={() => onToggleHandled(escalation.id)}
                onUpdate={onUpdate}
                updatingAppointmentId={updatingAppointmentId}
              />
            )
          })}
        </ul>
      </section>
    </section>
  )
}

function EscalationReviewCard({
  appointment,
  appointmentDraft,
  compact = false,
  draft,
  escalation,
  isSaving,
  onAppointmentDraftChange,
  onAppointmentSave,
  onDraftChange,
  onToggle,
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
    <li className={`escalation-card${compact ? ' is-compact' : ''}`}>
      <span>
        <strong>
          {patient} - {formatConstant(escalation.urgency)}
        </strong>
        <small>{workflow}</small>
        <small>
          Report day {report.day_after_treatment}: pain {report.pain_level}/10, swelling{' '}
          {formatConstant(report.swelling)}, fever {formatBoolean(report.fever)}
        </small>
        {compact ? (
          <>
            {escalation.staff_response ? (
              <small>Response: {escalation.staff_response}</small>
            ) : null}
            {appointment ? <AppointmentSummary appointment={appointment} /> : null}
            <button className="secondary-button compact-button" onClick={onToggle} type="button">
              Edit review
            </button>
          </>
        ) : (
          <>
            <small>
              Risk action: {formatConstant(escalation.risk_assessment_detail?.recommended_action)}
            </small>
            {escalation.advice_message ? (
              <small>Bounded advice: {escalation.advice_message.message}</small>
            ) : null}
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
                {onToggle ? (
                  <button className="secondary-button compact-button" onClick={onToggle} type="button">
                    Collapse
                  </button>
                ) : null}
              </div>
            </div>
          </>
        )}
      </span>
      <span className={`status-badge ${statusClass(escalation.status)}`}>
        {formatConstant(escalation.status)}
      </span>
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
