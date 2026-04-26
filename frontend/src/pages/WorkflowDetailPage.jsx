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
  listAdviceBoundaries,
  listCareStages,
  listEscalationRules,
  listSymptomDefinitions,
  listSymptomRules,
  updateWorkflow,
  validateWorkflow,
} from '../api/workflows.js'
import { useAuth } from '../auth/useAuth.js'

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
    ] = await Promise.all([
      getWorkflow(workflowId),
      listCareStages(),
      listSymptomDefinitions(),
      listSymptomRules(),
      listAdviceBoundaries(),
      listEscalationRules(),
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
          <p className="eyebrow">Workflow draft</p>
          <h1>{workflow.name}</h1>
          <span className={`status-badge status-${workflow.status.toLowerCase()}`}>
            {workflow.status}
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
            {validationResult ? <ValidationResult result={validationResult} /> : null}
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
            <button className="primary-button" type="submit">
              Save workflow
            </button>
          </form>
        </Section>

        <Section title="Care Stages">
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
            <button className="primary-button" type="submit">
              Add stage
            </button>
          </form>
          <ResourceList items={stages} getText={(stage) => `${stage.name}: day ${stage.start_day}-${stage.end_day}`} />
        </Section>

        <Section title="Symptoms">
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
            <button className="primary-button" type="submit">
              Add symptom
            </button>
          </form>
          <ResourceList items={symptoms} getText={(symptom) => `${symptom.key}: ${symptom.label}`} />
        </Section>

        <Section title="Symptom Rules">
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
            <button className="primary-button" type="submit">
              Add rule
            </button>
          </form>
          <ResourceList items={rules} getText={(rule) => `${rule.name}: ${rule.risk_level}`} />
        </Section>

        <Section title="AI Advice Boundaries">
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
            <button className="primary-button" type="submit">
              Add boundary
            </button>
          </form>
          <ResourceList items={boundaries} getText={(boundary) => `Boundary ${boundary.id}`} />
        </Section>

        <Section title="Escalation Rules">
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
            <button className="primary-button" type="submit">
              Add escalation
            </button>
          </form>
          <ResourceList items={escalations} getText={(item) => `${item.target_role}: ${item.urgency}`} />
        </Section>
      </div>
    </main>
  )
}

function ValidationResult({ result }) {
  return (
    <section className={result.is_valid ? 'validation-box is-valid' : 'validation-box is-invalid'}>
      <strong>{result.is_valid ? 'Workflow is valid.' : 'Workflow needs changes.'}</strong>
      {result.errors?.length ? (
        <ul>
          {result.errors.map((message) => (
            <li key={message}>{message}</li>
          ))}
        </ul>
      ) : null}
      {result.warnings?.length ? (
        <ul>
          {result.warnings.map((message) => (
            <li key={message}>{message}</li>
          ))}
        </ul>
      ) : null}
    </section>
  )
}

function ResourceList({ items, getText }) {
  if (items.length === 0) {
    return <p className="muted-text">None yet.</p>
  }

  return (
    <ul className="resource-list compact-list">
      {items.map((item) => (
        <li key={item.id}>
          <span>{getText(item)}</span>
        </li>
      ))}
    </ul>
  )
}
