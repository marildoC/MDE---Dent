import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  activateWorkflow,
  archiveWorkflow,
  createAdviceBoundary,
  createCareStage,
  createEscalationRule,
  createSymptomDefinition,
  createSymptomRule,
  getWorkflow,
  getWorkflowValidationReport,
  listAdviceBoundaries,
  listCareStages,
  listEscalationRules,
  listSymptomDefinitions,
  listSymptomRules,
  updateWorkflow,
  validateWorkflow,
} from '../api/workflows.js'
import { useAuth } from '../auth/useAuth.js'
import { formatConstant, statusClass } from '../utils/display.js'

const emptyStage = { name: '', start_day: '', end_day: '', description: '', sort_order: 0 }
const emptySymptom = {
  key: '',
  label: '',
  data_type: 'INTEGER',
  allowed_values: '',
  min_value: '',
  max_value: '',
  description: '',
  is_required: true,
}
const emptyRule = {
  stage: '',
  name: '',
  condition: '{\n  "all": [\n    {"field": "pain_level", "operator": ">=", "value": 8}\n  ]\n}',
  risk_level: 'HIGH',
  recommended_action: 'ESCALATE_TO_DENTIST',
  appointment_priority: 'HIGH',
  explanation: '',
}
const emptyBoundary = {
  stage: '',
  allowed_topics: 'aftercare reminders',
  forbidden_topics: 'diagnosis,prescription',
  required_disclaimer: '',
}
const emptyEscalation = {
  symptom_rule: '',
  target_role: 'DENTIST',
  urgency: 'HIGH',
  appointment_priority: 'HIGH',
  message: '',
}

const executionSteps = [
  'Once active, this workflow can be assigned to a patient as a follow-up case with a treatment date.',
  'When the patient submits a report, the system derives the day after treatment.',
  'The system detects the care stage whose day range contains that report day.',
  'Only rules belonging to the detected care stage are considered.',
  'Rule conditions are evaluated from structured JSON using controlled operators.',
  'If multiple rules match, the highest risk level is selected.',
  'A RiskAssessment is persisted with detected stage, matched rules, risk, recommended action, appointment priority, and explanation.',
  'Bounded advice is generated from the selected risk/action and the workflow AI advice boundaries.',
  'HIGH/URGENT results create staff escalation according to escalation rules.',
  'Appointment handling can then use the risk/escalation context.',
  'Audit records preserve traceability.',
]

function csvToList(value) {
  return value
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)
}

function optionalInteger(value) {
  return value === '' ? null : Number(value)
}

function Section({ title, children }) {
  return (
    <section className="section-panel">
      <h2>{title}</h2>
      {children}
    </section>
  )
}

function ActiveWorkflowNotice() {
  return (
    <p className="state-note">
      This workflow is active. Version 1 protects active workflow structures from direct edits.
    </p>
  )
}

export default function WorkflowDetailPage() {
  const { workflowId } = useParams()
  const { logout } = useAuth()
  const [workflow, setWorkflow] = useState(null)
  const [workflowForm, setWorkflowForm] = useState(null)
  const [stages, setStages] = useState([])
  const [symptoms, setSymptoms] = useState([])
  const [rules, setRules] = useState([])
  const [boundaries, setBoundaries] = useState([])
  const [escalations, setEscalations] = useState([])
  const [stageForm, setStageForm] = useState(emptyStage)
  const [symptomForm, setSymptomForm] = useState(emptySymptom)
  const [ruleForm, setRuleForm] = useState(emptyRule)
  const [boundaryForm, setBoundaryForm] = useState(emptyBoundary)
  const [escalationForm, setEscalationForm] = useState(emptyEscalation)
  const [error, setError] = useState('')
  const [validationResult, setValidationResult] = useState(null)

  const fetchWorkflowData = useCallback(async () => {
    const [
      workflowData,
      allStages,
      allSymptoms,
      allRules,
      allBoundaries,
      allEscalations,
      validationReport,
    ] = await Promise.all([
      getWorkflow(workflowId),
      listCareStages(),
      listSymptomDefinitions(),
      listSymptomRules(),
      listAdviceBoundaries(),
      listEscalationRules(),
      getWorkflowValidationReport(workflowId),
    ])

    const workflowStages = allStages.filter((stage) => String(stage.workflow) === workflowId)
    const stageIds = new Set(workflowStages.map((stage) => stage.id))
    const workflowRules = allRules.filter((rule) => stageIds.has(rule.stage))
    const ruleIds = new Set(workflowRules.map((rule) => rule.id))

    return {
      boundaries: allBoundaries.filter((boundary) => String(boundary.workflow) === workflowId),
      escalations: allEscalations.filter((escalation) => ruleIds.has(escalation.symptom_rule)),
      rules: workflowRules,
      stages: workflowStages,
      symptoms: allSymptoms.filter((symptom) => String(symptom.workflow) === workflowId),
      validationReport,
      workflowData,
    }
  }, [workflowId])

  const loadData = useCallback(async () => {
    const data = await fetchWorkflowData()
    setWorkflow(data.workflowData)
    setWorkflowForm({
      name: data.workflowData.name,
      treatment_type: data.workflowData.treatment_type,
      status: data.workflowData.status,
      description: data.workflowData.description || '',
    })
    setStages(data.stages)
    setSymptoms(data.symptoms)
    setRules(data.rules)
    setBoundaries(data.boundaries)
    setEscalations(data.escalations)
    setValidationResult(data.validationReport)
  }, [fetchWorkflowData])

  useEffect(() => {
    let isMounted = true

    fetchWorkflowData()
      .then((data) => {
        if (!isMounted) {
          return
        }
        setWorkflow(data.workflowData)
        setWorkflowForm({
          name: data.workflowData.name,
          treatment_type: data.workflowData.treatment_type,
          status: data.workflowData.status,
          description: data.workflowData.description || '',
        })
        setStages(data.stages)
        setSymptoms(data.symptoms)
        setRules(data.rules)
        setBoundaries(data.boundaries)
        setEscalations(data.escalations)
        setValidationResult(data.validationReport)
      })
      .catch((err) => {
        if (isMounted) {
          setError(err.message)
        }
      })

    return () => {
      isMounted = false
    }
  }, [fetchWorkflowData])

  const stageOptions = useMemo(
    () => stages.map((stage) => ({ value: stage.id, label: stage.name })),
    [stages],
  )

  const ruleOptions = useMemo(
    () => rules.map((rule) => ({ value: rule.id, label: rule.name })),
    [rules],
  )

  async function submitAndReload(callback) {
    setError('')
    try {
      await callback()
      await loadData()
    } catch (err) {
      setError(err.message)
    }
  }

  async function runLifecycleAction(callback) {
    setError('')
    try {
      const result = await callback()
      setValidationResult(result.is_valid === undefined ? null : result)
      await loadData()
    } catch (err) {
      setError(err.message)
    }
  }

  const handleValidate = () => {
    runLifecycleAction(() => validateWorkflow(workflowId))
  }

  const handleActivate = () => {
    runLifecycleAction(() => activateWorkflow(workflowId))
  }

  const handleArchive = () => {
    runLifecycleAction(() => archiveWorkflow(workflowId))
  }

  const submitWorkflow = (event) => {
    event.preventDefault()
    submitAndReload(() => updateWorkflow(workflowId, workflowForm))
  }

  const submitStage = (event) => {
    event.preventDefault()
    submitAndReload(async () => {
      await createCareStage({
        ...stageForm,
        workflow: Number(workflowId),
        start_day: Number(stageForm.start_day),
        end_day: Number(stageForm.end_day),
        sort_order: Number(stageForm.sort_order || 0),
      })
      setStageForm(emptyStage)
    })
  }

  const submitSymptom = (event) => {
    event.preventDefault()
    submitAndReload(async () => {
      await createSymptomDefinition({
        ...symptomForm,
        workflow: Number(workflowId),
        allowed_values: csvToList(symptomForm.allowed_values),
        min_value: optionalInteger(symptomForm.min_value),
        max_value: optionalInteger(symptomForm.max_value),
      })
      setSymptomForm(emptySymptom)
    })
  }

  const submitRule = (event) => {
    event.preventDefault()
    submitAndReload(async () => {
      await createSymptomRule({
        ...ruleForm,
        stage: Number(ruleForm.stage),
        condition: JSON.parse(ruleForm.condition),
      })
      setRuleForm(emptyRule)
    })
  }

  const submitBoundary = (event) => {
    event.preventDefault()
    submitAndReload(async () => {
      await createAdviceBoundary({
        ...boundaryForm,
        workflow: Number(workflowId),
        stage: boundaryForm.stage ? Number(boundaryForm.stage) : null,
        allowed_topics: csvToList(boundaryForm.allowed_topics),
        forbidden_topics: csvToList(boundaryForm.forbidden_topics),
      })
      setBoundaryForm(emptyBoundary)
    })
  }

  const submitEscalation = (event) => {
    event.preventDefault()
    submitAndReload(async () => {
      await createEscalationRule({
        ...escalationForm,
        symptom_rule: Number(escalationForm.symptom_rule),
      })
      setEscalationForm(emptyEscalation)
    })
  }

  if (!workflow || !workflowForm) {
    return (
      <main className="app-shell">
        <section className="status-panel">Loading workflow...</section>
      </main>
    )
  }

  const isActive = workflow.status === 'ACTIVE'

  return (
    <main className="app-shell">
      <header className="top-bar">
        <div>
          <p className="eyebrow">Workflow model</p>
          <h1>{workflow.name}</h1>
          <span className={`status-badge ${statusClass(workflow.status)}`}>
            {formatConstant(workflow.status)}
          </span>
        </div>
        <div className="button-row">
          <Link className="secondary-link" to="/admin/workflows">
            Workflows
          </Link>
          <button className="secondary-button" type="button" onClick={logout}>
            Logout
          </button>
        </div>
      </header>

      {error ? <p className="form-error page-error">{error}</p> : null}

      <div className="workflow-grid">
        <Section title="Workflow">
          <div className="lifecycle-panel">
            {isActive ? <ActiveWorkflowNotice /> : null}
            <div className="button-row">
              <button className="primary-button" type="button" onClick={handleValidate}>
                Validate
              </button>
              <button
                className="secondary-button"
                disabled={workflow.status !== 'VALIDATED'}
                type="button"
                onClick={handleActivate}
              >
                Activate
              </button>
              <button
                className="secondary-button"
                disabled={workflow.status !== 'ACTIVE'}
                type="button"
                onClick={handleArchive}
              >
                Archive
              </button>
            </div>
          </div>
          <form className="panel-form compact-form" onSubmit={submitWorkflow}>
            <label>
              Name
              <input
                disabled={isActive}
                name="name"
                onChange={(event) =>
                  setWorkflowForm((current) => ({ ...current, name: event.target.value }))
                }
                required
                value={workflowForm.name}
              />
            </label>
            <label>
              Description
              <textarea
                disabled={isActive}
                name="description"
                onChange={(event) =>
                  setWorkflowForm((current) => ({
                    ...current,
                    description: event.target.value,
                  }))
                }
                value={workflowForm.description}
              />
            </label>
            <button className="primary-button" disabled={isActive} type="submit">
              Save workflow
            </button>
          </form>
        </Section>

        <Section title="Care Stages">
          {isActive ? <ActiveWorkflowNotice /> : null}
          <form className="panel-form compact-form" onSubmit={submitStage}>
            <input
              placeholder="Name"
              required
              value={stageForm.name}
              onChange={(event) => setStageForm((current) => ({ ...current, name: event.target.value }))}
            />
            <div className="inline-fields">
              <input
                min="0"
                placeholder="Start day"
                required
                type="number"
                value={stageForm.start_day}
                onChange={(event) =>
                  setStageForm((current) => ({ ...current, start_day: event.target.value }))
                }
              />
              <input
                min="0"
                placeholder="End day"
                required
                type="number"
                value={stageForm.end_day}
                onChange={(event) =>
                  setStageForm((current) => ({ ...current, end_day: event.target.value }))
                }
              />
            </div>
            <textarea
              placeholder="Description"
              value={stageForm.description}
              onChange={(event) =>
                setStageForm((current) => ({ ...current, description: event.target.value }))
              }
            />
            <button className="primary-button" disabled={isActive} type="submit">
              Add stage
            </button>
          </form>
          <ResourceList items={stages} getText={(stage) => `${stage.name}: day ${stage.start_day}-${stage.end_day}`} />
        </Section>

        <Section title="Symptoms">
          {isActive ? <ActiveWorkflowNotice /> : null}
          <form className="panel-form compact-form" onSubmit={submitSymptom}>
            <div className="inline-fields">
              <input
                placeholder="Key"
                required
                value={symptomForm.key}
                onChange={(event) =>
                  setSymptomForm((current) => ({ ...current, key: event.target.value }))
                }
              />
              <input
                placeholder="Label"
                required
                value={symptomForm.label}
                onChange={(event) =>
                  setSymptomForm((current) => ({ ...current, label: event.target.value }))
                }
              />
            </div>
            <select
              value={symptomForm.data_type}
              onChange={(event) =>
                setSymptomForm((current) => ({ ...current, data_type: event.target.value }))
              }
            >
              <option value="INTEGER">Integer</option>
              <option value="BOOLEAN">Boolean</option>
              <option value="CHOICE">Choice</option>
              <option value="TEXT">Text</option>
            </select>
            <input
              placeholder="Allowed values, comma separated"
              value={symptomForm.allowed_values}
              onChange={(event) =>
                setSymptomForm((current) => ({ ...current, allowed_values: event.target.value }))
              }
            />
            <button className="primary-button" disabled={isActive} type="submit">
              Add symptom
            </button>
          </form>
          <ResourceList
            items={symptoms}
            getText={(symptom) => `${symptom.label} (${symptom.key}) - ${formatConstant(symptom.data_type)}`}
          />
        </Section>

        <Section title="Symptom Rules">
          {isActive ? <ActiveWorkflowNotice /> : null}
          <form className="panel-form compact-form" onSubmit={submitRule}>
            <select
              required
              value={ruleForm.stage}
              onChange={(event) => setRuleForm((current) => ({ ...current, stage: event.target.value }))}
            >
              <option value="">Select stage</option>
              {stageOptions.map((stage) => (
                <option key={stage.value} value={stage.value}>
                  {stage.label}
                </option>
              ))}
            </select>
            <input
              placeholder="Rule name"
              required
              value={ruleForm.name}
              onChange={(event) => setRuleForm((current) => ({ ...current, name: event.target.value }))}
            />
            <textarea
              className="code-textarea"
              required
              value={ruleForm.condition}
              onChange={(event) =>
                setRuleForm((current) => ({ ...current, condition: event.target.value }))
              }
            />
            <div className="inline-fields">
              <select
                value={ruleForm.risk_level}
                onChange={(event) =>
                  setRuleForm((current) => ({ ...current, risk_level: event.target.value }))
                }
              >
                <option value="LOW">Low</option>
                <option value="WARNING">Warning</option>
                <option value="HIGH">High</option>
                <option value="URGENT">Urgent</option>
              </select>
              <select
                value={ruleForm.recommended_action}
                onChange={(event) =>
                  setRuleForm((current) => ({
                    ...current,
                    recommended_action: event.target.value,
                  }))
                }
              >
                <option value="SHOW_ADVICE">Show advice</option>
                <option value="CONTINUE_MONITORING">Continue monitoring</option>
                <option value="RECOMMEND_CONTACT">Recommend contact</option>
                <option value="ESCALATE_TO_DENTIST">Escalate to dentist</option>
                <option value="PRIORITIZE_APPOINTMENT">Prioritize appointment</option>
              </select>
            </div>
            <textarea
              placeholder="Explanation"
              required
              value={ruleForm.explanation}
              onChange={(event) =>
                setRuleForm((current) => ({ ...current, explanation: event.target.value }))
              }
            />
            <button className="primary-button" disabled={isActive} type="submit">
              Add rule
            </button>
          </form>
          <ResourceList
            items={rules}
            renderItem={(rule) => (
              <span className="rule-summary">
                <strong>Rule: {rule.name}</strong>
                <small>When: {rule.condition_text || 'Unsupported condition structure'}</small>
                <small>Risk: {formatConstant(rule.risk_level)}</small>
                <small>Action: {formatConstant(rule.recommended_action)}</small>
                <small>Appointment priority: {formatConstant(rule.appointment_priority)}</small>
              </span>
            )}
          />
        </Section>

        <Section title="AI Constraints">
          {isActive ? <ActiveWorkflowNotice /> : null}
          <form className="panel-form compact-form" onSubmit={submitBoundary}>
            <select
              value={boundaryForm.stage}
              onChange={(event) =>
                setBoundaryForm((current) => ({ ...current, stage: event.target.value }))
              }
            >
              <option value="">Workflow-level</option>
              {stageOptions.map((stage) => (
                <option key={stage.value} value={stage.value}>
                  {stage.label}
                </option>
              ))}
            </select>
            <input
              placeholder="Allowed topics"
              value={boundaryForm.allowed_topics}
              onChange={(event) =>
                setBoundaryForm((current) => ({ ...current, allowed_topics: event.target.value }))
              }
            />
            <input
              placeholder="Forbidden topics"
              value={boundaryForm.forbidden_topics}
              onChange={(event) =>
                setBoundaryForm((current) => ({ ...current, forbidden_topics: event.target.value }))
              }
            />
            <textarea
              placeholder="Required disclaimer"
              value={boundaryForm.required_disclaimer}
              onChange={(event) =>
                setBoundaryForm((current) => ({
                  ...current,
                  required_disclaimer: event.target.value,
                }))
              }
            />
            <button className="primary-button" disabled={isActive} type="submit">
              Add boundary
            </button>
          </form>
          <ResourceList
            items={boundaries}
            getText={(boundary) =>
              `Boundary ${boundary.id}: forbids ${(boundary.forbidden_topics || [])
                .map(formatConstant)
                .join(', ')}`
            }
          />
        </Section>

        <Section title="Staff Escalation Rules">
          {isActive ? <ActiveWorkflowNotice /> : null}
          <form className="panel-form compact-form" onSubmit={submitEscalation}>
            <select
              required
              value={escalationForm.symptom_rule}
              onChange={(event) =>
                setEscalationForm((current) => ({ ...current, symptom_rule: event.target.value }))
              }
            >
              <option value="">Select symptom rule</option>
              {ruleOptions.map((rule) => (
                <option key={rule.value} value={rule.value}>
                  {rule.label}
                </option>
              ))}
            </select>
            <div className="inline-fields">
              <select
                value={escalationForm.urgency}
                onChange={(event) =>
                  setEscalationForm((current) => ({ ...current, urgency: event.target.value }))
                }
              >
                <option value="HIGH">High</option>
                <option value="URGENT">Urgent</option>
              </select>
              <select
                value={escalationForm.appointment_priority}
                onChange={(event) =>
                  setEscalationForm((current) => ({
                    ...current,
                    appointment_priority: event.target.value,
                  }))
                }
              >
                <option value="HIGH">High</option>
                <option value="URGENT">Urgent</option>
              </select>
            </div>
            <textarea
              placeholder="Message"
              required
              value={escalationForm.message}
              onChange={(event) =>
                setEscalationForm((current) => ({ ...current, message: event.target.value }))
              }
            />
            <button className="primary-button" disabled={isActive} type="submit">
              Add escalation
            </button>
          </form>
          <ResourceList
            items={escalations}
            getText={(item) =>
              `${formatConstant(item.target_role)} review: ${formatConstant(
                item.urgency,
              )} urgency, ${formatConstant(item.appointment_priority)} appointment priority`
            }
          />
        </Section>

        <StaticSemanticsPanel result={validationResult} workflowStatus={workflow.status} />

        <ExecutionSemanticsPanel
          boundaries={boundaries}
          escalations={escalations}
          rules={rules}
          stages={stages}
          symptoms={symptoms}
          workflow={workflow}
        />
      </div>
    </main>
  )
}

function StaticSemanticsPanel({ result, workflowStatus }) {
  const overallLabel = result ? (result.is_valid ? 'Valid' : 'Invalid') : 'Not validated'
  const overallClass = result ? (result.is_valid ? 'is-valid' : 'is-invalid') : 'status-draft'

  return (
    <section className="section-panel validation-panel">
      <div className="validation-summary">
        <div>
          <p className="eyebrow">Workflow DSL Studio</p>
          <h2>Static Semantics / Validation</h2>
          <p className="muted-text">
            Checks whether this workflow model is semantically valid before it can be activated.
          </p>
        </div>
        <span className={`status-badge ${overallClass}`}>{overallLabel}</span>
      </div>
      <p className="muted-text validation-context">
        Workflow status: {formatConstant(workflowStatus)}
      </p>
      {result?.checks?.length ? (
        <ul className="semantic-check-list">
          {result.checks.map((check) => (
            <li className={`semantic-check semantic-check-${check.status}`} key={check.key}>
              <span className="semantic-check-marker">{semanticCheckMarker(check.status)}</span>
              <span>
                <strong>{check.label}</strong>
                {check.message ? <small>{check.message}</small> : null}
              </span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="muted-text">Run validation to inspect this workflow model.</p>
      )}
    </section>
  )
}

function semanticCheckMarker(status) {
  if (status === 'pass') {
    return 'PASS'
  }
  if (status === 'warning') {
    return 'WARN'
  }
  return 'FAIL'
}

function ExecutionSemanticsPanel({ boundaries, escalations, rules, stages, symptoms, workflow }) {
  const facts = [
    { label: 'Workflow status', value: formatConstant(workflow.status) },
    { label: 'Care stages', value: stages.length },
    { label: 'Symptom definitions', value: symptoms.length },
    { label: 'Symptom rules', value: rules.length },
    { label: 'Advice boundaries', value: boundaries.length },
    { label: 'Escalation rules', value: escalations.length },
  ]

  return (
    <section className="section-panel execution-panel">
      <div>
        <p className="eyebrow">Workflow DSL Studio</p>
        <h2>Execution Semantics</h2>
        <p className="muted-text">
          Shows how this workflow model is interpreted when a patient submits a symptom report.
        </p>
      </div>

      <dl className="execution-facts">
        {facts.map((fact) => (
          <div key={fact.label}>
            <dt>{fact.label}</dt>
            <dd>{fact.value}</dd>
          </div>
        ))}
      </dl>

      <ol className="execution-step-list">
        {executionSteps.map((step) => (
          <li key={step}>
            <span>{step}</span>
          </li>
        ))}
      </ol>
    </section>
  )
}

function ResourceList({ items, getText, renderItem }) {
  if (items.length === 0) {
    return <p className="muted-text">None yet.</p>
  }

  return (
    <ul className="resource-list compact-list">
      {items.map((item) => (
        <li key={item.id}>
          {renderItem ? renderItem(item) : <span>{getText(item)}</span>}
        </li>
      ))}
    </ul>
  )
}
