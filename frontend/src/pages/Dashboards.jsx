import { Link } from 'react-router-dom'
import { useEffect, useMemo, useState } from 'react'
import { generateAdvice } from '../api/aiSupport.js'
import { listAppointments } from '../api/appointments.js'
import { evaluateReport } from '../api/decisionEngine.js'
import { listEscalationCases } from '../api/escalations.js'
import { listMyFollowUpCases } from '../api/patients.js'
import { createSymptomReport, listSymptomReports } from '../api/reports.js'
import { useAuth } from '../auth/useAuth.js'
import {
  formatBoolean,
  formatConstant,
  formatDateTime,
  riskClass,
  statusClass,
} from '../utils/display.js'

const dashboardCopy = {
  patient: {
    eyebrow: 'Patient area',
    title: 'Patient Dashboard',
    body: 'Follow your assigned recovery workflow, submit reports, and review staff updates.',
  },
  staff: {
    eyebrow: 'Dentist and staff area',
    title: 'Dentist/Staff Dashboard',
    body: 'Review follow-up cases, escalations, and appointment priorities.',
  },
  admin: {
    eyebrow: 'Admin area',
    title: 'Admin Dashboard',
    body: 'Manage workflows, runtime cases, and audit traceability.',
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

const terminalCaseStatuses = new Set(['RESOLVED', 'CLOSED'])

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

      {variant === 'admin' ? (
        <section className="dashboard-panel admin-dashboard-panel">
          <div className="admin-dashboard-intro">
            <p className="eyebrow">Operational controls</p>
            <h2>Manage the implemented DentCare-MDE follow-up system.</h2>
            <p className="muted-text">Signed in as {user.username}</p>
          </div>
          <div className="admin-action-grid">
            <AdminActionCard
              body="Create, validate, activate, and archive dental workflows."
              label="Workflow Management"
              to="/admin/workflows"
            />
            <AdminActionCard
              body="Create patient profiles, assign workflows, and review reports, escalations, and appointments."
              label="Follow-Up Cases"
              to="/follow-up-cases"
            />
            <AdminActionCard
              body="Ask read-only operational questions about clinic data."
              label="Admin Intelligence"
              to="/admin-intelligence"
            />
          </div>
        </section>
      ) : variant === 'staff' ? (
        <section className="dashboard-panel admin-dashboard-panel staff-dashboard-panel">
          <div className="admin-dashboard-intro">
            <p className="eyebrow">Staff review</p>
            <h2>Review follow-up cases, escalations, and appointment priorities.</h2>
            <p className="muted-text">Signed in as {user.username}</p>
          </div>
          <div className="admin-action-grid staff-action-grid">
            <AdminActionCard
              body="Review patient reports, escalations, staff responses, and appointments."
              label="Follow-up cases"
              to="/follow-up-cases"
            />
          </div>
        </section>
      ) : (
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
      )}
    </main>
  )
}

function AdminActionCard({ body, label, to }) {
  return (
    <Link className="admin-action-card" to={to}>
      <span>
        <strong>{label}</strong>
        <small>{body}</small>
      </span>
      <span className="admin-action-arrow">Open</span>
    </Link>
  )
}

export function PatientDashboard() {
  const { logout } = useAuth()
  const [followUpCases, setFollowUpCases] = useState([])
  const [selectedCaseIndex, setSelectedCaseIndex] = useState(0)
  const [appointments, setAppointments] = useState([])
  const [escalations, setEscalations] = useState([])
  const [reports, setReports] = useState([])
  const [expandedReportIds, setExpandedReportIds] = useState(new Set())
  const [reportForm, setReportForm] = useState(reportInitial)
  const [reportFormKey, setReportFormKey] = useState(0)
  const [isLoading, setIsLoading] = useState(true)
  const [evaluatingReportId, setEvaluatingReportId] = useState(null)
  const [generatingAdviceId, setGeneratingAdviceId] = useState(null)
  const [isSubmittingReport, setIsSubmittingReport] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const activeCase = followUpCases[selectedCaseIndex] || null
  const sortedReports = useMemo(() => sortReportsNewestFirst(reports), [reports])

  useEffect(() => {
    let isMounted = true

    listMyFollowUpCases()
      .then((data) => {
        if (isMounted) {
          setFollowUpCases(data)
          setSelectedCaseIndex(0)
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

  useEffect(() => {
    let isMounted = true

    if (!activeCase) {
      return () => {
        isMounted = false
      }
    }

    Promise.all([
      listAppointments({ followUpCaseId: activeCase.id }),
      listSymptomReports({ followUpCaseId: activeCase.id }),
      listEscalationCases({ followUpCaseId: activeCase.id }),
    ])
      .then(([appointmentsData, reportsData, escalationsData]) => {
        if (isMounted) {
          setAppointments(appointmentsData)
          setReports(reportsData)
          setEscalations(escalationsData)
          setExpandedReportIds(defaultExpandedReportIds(reportsData))
        }
      })
      .catch((err) => {
        if (isMounted) {
          setError(err.message)
          setAppointments([])
          setReports([])
          setEscalations([])
        }
      })

    return () => {
      isMounted = false
    }
  }, [activeCase])

  const loadReports = async (caseId) => {
    const [appointmentsData, reportsData, escalationsData] = await Promise.all([
      listAppointments({ followUpCaseId: caseId }),
      listSymptomReports({ followUpCaseId: caseId }),
      listEscalationCases({ followUpCaseId: caseId }),
    ])
    setAppointments(appointmentsData)
    setReports(reportsData)
    setEscalations(escalationsData)
    setExpandedReportIds(defaultExpandedReportIds(reportsData))
  }

  const handleReportChange = (event) => {
    const { files, name, value } = event.target
    setReportForm((current) => ({
      ...current,
      [name]: files ? files[0] || null : value,
    }))
  }

  const switchCase = () => {
    if (followUpCases.length <= 1) {
      return
    }

    setError('')
    setMessage('')
    setAppointments([])
    setReports([])
    setEscalations([])
    setReportForm(reportInitial)
    setExpandedReportIds(new Set())
    setReportFormKey((current) => current + 1)
    setSelectedCaseIndex((current) => (current + 1) % followUpCases.length)
  }

  const toggleReport = (reportId) => {
    setExpandedReportIds((current) => {
      const next = new Set(current)
      if (next.has(reportId)) {
        next.delete(reportId)
      } else {
        next.add(reportId)
      }
      return next
    })
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

  const handleEvaluateReport = async (reportId) => {
    if (!activeCase) {
      return
    }

    setError('')
    setEvaluatingReportId(reportId)
    try {
      await evaluateReport(reportId)
      await loadReports(activeCase.id)
    } catch (err) {
      setError(err.message)
    } finally {
      setEvaluatingReportId(null)
    }
  }

  const handleGenerateAdvice = async (assessmentId) => {
    if (!activeCase) {
      return
    }

    setError('')
    setGeneratingAdviceId(assessmentId)
    try {
      await generateAdvice(assessmentId)
      await loadReports(activeCase.id)
    } catch (err) {
      setError(err.message)
    } finally {
      setGeneratingAdviceId(null)
    }
  }

  return (
    <main className="app-shell">
      <header className="top-bar patient-top-bar">
        <div>
          <p className="eyebrow">Patient</p>
          <h1>Patient Dashboard</h1>
        </div>
        <button className="secondary-button" type="button" onClick={logout}>
          Logout
        </button>
      </header>

      <section className="dashboard-panel patient-dashboard-panel">
        <div>
          {isLoading ? <h2>Loading follow-up case...</h2> : null}
          {!isLoading && !activeCase ? <h2>No active follow-up case yet.</h2> : null}
          {activeCase ? (
            <ActiveCaseSummary
              activeCase={activeCase}
              caseCount={followUpCases.length}
              onSwitchCase={switchCase}
              selectedCaseIndex={selectedCaseIndex}
            />
          ) : null}
          {activeCase ? (
            <SymptomReportSection
              activeCase={activeCase}
              appointments={appointments}
              form={reportForm}
              formKey={reportFormKey}
              expandedReportIds={expandedReportIds}
              isSubmitting={isSubmittingReport}
              message={message}
              onChange={handleReportChange}
              onEvaluate={handleEvaluateReport}
              onGenerateAdvice={handleGenerateAdvice}
              onSubmit={submitReport}
              onToggleReport={toggleReport}
              escalations={escalations}
              reports={sortedReports}
              evaluatingReportId={evaluatingReportId}
              generatingAdviceId={generatingAdviceId}
            />
          ) : null}
          {error ? <p className="form-error">{error}</p> : null}
        </div>
      </section>
    </main>
  )
}

function sortReportsNewestFirst(items) {
  return [...items].sort((first, second) => {
    const firstTime = new Date(first.created_at || 0).getTime()
    const secondTime = new Date(second.created_at || 0).getTime()
    return secondTime - firstTime || second.id - first.id
  })
}

function defaultExpandedReportIds(items) {
  const newestReport = sortReportsNewestFirst(items)[0]
  return newestReport ? new Set([newestReport.id]) : new Set()
}

export function StaffDashboard() {
  return <DashboardLayout variant="staff" />
}

export function AdminDashboard() {
  return <DashboardLayout variant="admin" />
}

function ActiveCaseSummary({ activeCase, caseCount, onSwitchCase, selectedCaseIndex }) {
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
      <div className="case-heading-row">
        <div>
          <p className="eyebrow">Current follow-up case</p>
          <h2>{workflow.name || 'Assigned workflow unavailable'}</h2>
          <p className="muted-text case-position">
            Case {selectedCaseIndex + 1} of {caseCount}
          </p>
          <StatusBadge value={activeCase.status} />
        </div>
        {caseCount > 1 ? (
          <div className="case-switcher">
            <button className="secondary-button" onClick={onSwitchCase} type="button">
              Switch case
            </button>
            <span aria-label="Follow-up case position" className="case-dots">
              {Array.from({ length: caseCount }).map((_, index) => (
                <span
                  aria-current={index === selectedCaseIndex ? 'true' : undefined}
                  className={`case-dot${index === selectedCaseIndex ? ' is-selected' : ''}`}
                  key={index}
                />
              ))}
            </span>
          </div>
        ) : (
          <span aria-label="Follow-up case position" className="case-dots">
            <span aria-current="true" className="case-dot is-selected" />
          </span>
        )}
      </div>
      <dl className="identity-list case-list">
        <div>
          <dt>Treatment type</dt>
          <dd>{formatConstant(workflow.treatment_type)}</dd>
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
          <dd>{formatConstant(activeCase.status)}</dd>
        </div>
      </dl>
    </div>
  )
}

function StatusBadge({ value }) {
  return <span className={`status-badge ${statusClass(value)}`}>{formatConstant(value)}</span>
}

function RiskBadge({ value }) {
  return <span className={`status-badge ${riskClass(value)}`}>{formatConstant(value)}</span>
}

function SymptomReportSection({
  activeCase,
  appointments,
  escalations,
  expandedReportIds,
  form,
  formKey,
  evaluatingReportId,
  generatingAdviceId,
  isSubmitting,
  message,
  onChange,
  onEvaluate,
  onGenerateAdvice,
  onSubmit,
  onToggleReport,
  reports,
}) {
  const canSubmitReport = !terminalCaseStatuses.has(activeCase.status)

  return (
    <div className="report-section">
      {canSubmitReport ? (
        <form className="compact-form report-form" key={formKey} onSubmit={onSubmit}>
          <h3>Submit symptom report</h3>
          <p className="muted-text form-context">
            Images are optional supporting evidence for staff review only.
          </p>
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
      ) : (
        <div className="terminal-case-notice">
          <h3>Symptom reporting closed</h3>
          <p>
            This follow-up case is {formatConstant(activeCase.status).toLowerCase()}. Previous reports and
            staff updates remain available below.
          </p>
        </div>
      )}

      <ReportHistory
        appointments={appointments}
        escalations={escalations}
        evaluatingReportId={evaluatingReportId}
        expandedReportIds={expandedReportIds}
        generatingAdviceId={generatingAdviceId}
        onEvaluate={onEvaluate}
        onGenerateAdvice={onGenerateAdvice}
        onToggleReport={onToggleReport}
        reports={reports}
      />
    </div>
  )
}

function ReportHistory({
  appointments,
  escalations,
  evaluatingReportId,
  expandedReportIds,
  generatingAdviceId,
  onEvaluate,
  onGenerateAdvice,
  onToggleReport,
  reports,
}) {
  const appointmentByEscalation = new Map(
    appointments.map((appointment) => [appointment.escalation_case, appointment]),
  )
  const escalationByReport = new Map(escalations.map((escalation) => [escalation.report, escalation]))

  return (
    <div className="report-history">
      <h3>Report history</h3>
      {reports.length === 0 ? <p className="muted-text">No symptom reports yet.</p> : null}
      <ul className="report-accordion-list">
        {reports.map((report) => (
          <ReportHistoryItem
            appointment={
              escalationByReport.get(report.id)
                ? appointmentByEscalation.get(escalationByReport.get(report.id).id)
                : null
            }
            escalation={escalationByReport.get(report.id)}
            evaluatingReportId={evaluatingReportId}
            generatingAdviceId={generatingAdviceId}
            isExpanded={expandedReportIds.has(report.id)}
            key={report.id}
            onEvaluate={onEvaluate}
            onGenerateAdvice={onGenerateAdvice}
            onToggle={() => onToggleReport(report.id)}
            report={report}
          />
        ))}
      </ul>
    </div>
  )
}

function ReportHistoryItem({
  appointment,
  escalation,
  evaluatingReportId,
  generatingAdviceId,
  isExpanded,
  onEvaluate,
  onGenerateAdvice,
  onToggle,
  report,
}) {
  const reportDate = formatReportDate(report.created_at)
  const reportTime = formatReportTime(report.created_at)

  return (
    <li className={`report-accordion-item${isExpanded ? ' is-expanded' : ''}`}>
      <button
        aria-expanded={isExpanded}
        className="report-accordion-trigger"
        onClick={onToggle}
        type="button"
      >
        <span>
          <strong>{reportDate}</strong>
          <small>
            {reportTime} | Day {report.day_after_treatment} | Pain {report.pain_level}/10
          </small>
        </span>
        <span className="chevron" aria-hidden="true">
          {isExpanded ? '⌃' : '⌄'}
        </span>
      </button>
      {isExpanded ? (
        <div className="report-accordion-body">
          <dl className="report-detail-grid">
            <div>
              <dt>Pain level</dt>
              <dd>{report.pain_level}/10</dd>
            </div>
            <div>
              <dt>Swelling</dt>
              <dd>{formatConstant(report.swelling)}</dd>
            </div>
            <div>
              <dt>Bleeding</dt>
              <dd>{formatConstant(report.bleeding)}</dd>
            </div>
            <div>
              <dt>Fever</dt>
              <dd>{formatBoolean(report.fever)}</dd>
            </div>
            <div>
              <dt>Bad smell/taste</dt>
              <dd>{formatBoolean(report.bad_smell)}</dd>
            </div>
          </dl>
          {report.notes ? <p className="report-notes">{report.notes}</p> : null}
          <RiskAssessmentSummary
            assessment={report.risk_assessment}
            appointment={appointment}
            escalation={escalation}
            evaluating={evaluatingReportId === report.id}
            generatingAdvice={generatingAdviceId === report.risk_assessment?.id}
            onEvaluate={() => onEvaluate(report.id)}
            onGenerateAdvice={() => onGenerateAdvice(report.risk_assessment.id)}
          />
        </div>
      ) : null}
    </li>
  )
}

function formatReportDate(value) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return 'Report date unavailable'
  }
  return date.toLocaleDateString()
}

function formatReportTime(value) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return 'Time unavailable'
  }
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
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
      {escalation.staff_response ? (
        <small>Staff response: {escalation.staff_response}</small>
      ) : (
        <small>This report has been sent to dental staff for review.</small>
      )}
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

function AdviceSummary({ advice, generating, onGenerate }) {
  if (advice) {
    return (
      <span className="advice-summary">
        <small className="advice-label">Supportive guidance</small>
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
