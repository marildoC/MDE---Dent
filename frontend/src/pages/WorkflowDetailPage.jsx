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
const emptyConditionRow = { field: '', operator: '=', value: '' }
const emptyRule = {
  stage: '',
  name: '',
  condition_match: 'all',
  conditions: [emptyConditionRow],
  risk_level: 'HIGH',
  recommended_action: 'ESCALATE_TO_DENTIST',
  appointment_priority: 'NONE',
  explanation: '',
}
const emptyBoundary = {
  stage: '',
  allowed_topics: 'aftercare reminders',
  forbidden_topics: 'diagnosis,prescription',
  required_disclaimer:
    'This guidance supports post-treatment follow-up only and does not replace dental diagnosis or prescription. Contact the clinic for worsening or urgent symptoms.',
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

const syntheticConditionFields = [
  {
    data_type: 'INTEGER',
    key: 'day_after_treatment',
    label: 'Day after treatment',
    max_value: null,
    min_value: 0,
  },
]

const numericOperators = ['=', '!=', '>', '>=', '<', '<=']
const booleanOperators = ['=', '!=']
const textOperators = ['=', '!=']

function csvToList(value) {
  return value
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)
}

function optionalInteger(value) {
  return value === '' ? null : Number(value)
}

function conditionFieldOptions(symptoms) {
  return [
    ...symptoms.map((symptom) => ({
      ...symptom,
      label: symptom.label || formatConstant(symptom.key),
    })),
    ...syntheticConditionFields,
  ]
}

function conditionFieldLabel(field) {
  return `${field.label || formatConstant(field.key)} (${field.key})`
}

function defaultValueForField(field) {
  if (!field) {
    return ''
  }

  if (field.data_type === 'BOOLEAN') {
    return false
  }

  if (field.data_type === 'INTEGER') {
    return field.min_value ?? 0
  }

  if (field.data_type === 'CHOICE') {
    return choiceValuesForField(field)[0] ?? ''
  }

  return ''
}

function choiceValuesForField(field) {
  if (!field?.allowed_values) {
    return []
  }

  if (Array.isArray(field.allowed_values)) {
    return field.allowed_values
  }

  return csvToList(String(field.allowed_values))
}

function operatorsForField(field) {
  if (!field) {
    return ['=']
  }

  if (field.data_type === 'INTEGER') {
    return numericOperators
  }

  if (field.data_type === 'BOOLEAN') {
    return booleanOperators
  }

  return textOperators
}

function normalizeOperator(field, operator) {
  const operators = operatorsForField(field)
  return operators.includes(operator) ? operator : operators[0]
}

function valueForCondition(field, value) {
  if (field?.data_type === 'INTEGER') {
    return Number(value)
  }

  if (field?.data_type === 'BOOLEAN') {
    return value === true || value === 'true'
  }

  return value
}

function buildConditionObject(ruleForm, fields) {
  return {
    [ruleForm.condition_match]: ruleForm.conditions.map((condition) => ({
      field: condition.field,
      operator: normalizeOperator(
        fields.find((field) => field.key === condition.field),
        condition.operator,
      ),
      value: valueForCondition(
        fields.find((field) => field.key === condition.field),
        condition.value,
      ),
    })),
  }
}

function formatConditionPreview(condition, matchMode = 'all') {
  if (!condition?.[matchMode]?.length) {
    return ''
  }

  const joiner = matchMode === 'any' ? ' OR ' : ' AND '
  return condition[matchMode]
    .map(
      (item) =>
        `${item.field} ${item.operator} ${formatConditionValue(item.value)}`,
    )
    .join(joiner)
}

function formatConditionValue(value) {
  if (typeof value === 'boolean') {
    return String(value)
  }

  if (Array.isArray(value)) {
    return `[${value.map(formatConditionValue).join(', ')}]`
  }

  if (value === null || value === undefined) {
    return 'null'
  }

  return String(value)
}

function withFieldDefinition(row, fields) {
  const fieldDefinition = fields.find((field) => field.key === row.field) || null
  return {
    ...row,
    fieldDefinition,
    operator: normalizeOperator(fieldDefinition, row.operator),
  }
}

function isConditionBuilderComplete(ruleForm) {
  return ruleForm.conditions.every((condition) => condition.field && condition.operator)
}

function Section({ className = '', title, children }) {
  return (
    <section className={`section-panel ${className}`.trim()}>
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

  const escalationRuleOptions = useMemo(() => {
    const escalatedRuleIds = new Set(escalations.map((item) => item.symptom_rule))
    return rules
      .filter(
        (rule) =>
          ['HIGH', 'URGENT'].includes(rule.risk_level) && !escalatedRuleIds.has(rule.id),
      )
      .map((rule) => ({
        appointmentPriority:
          rule.appointment_priority && rule.appointment_priority !== 'NONE'
            ? rule.appointment_priority
            : rule.risk_level,
        label: `${rule.name} (${formatConstant(rule.risk_level)})`,
        riskLevel: rule.risk_level,
        value: rule.id,
      }))
  }, [escalations, rules])

  const conditionFields = useMemo(() => conditionFieldOptions(symptoms), [symptoms])

  const conditionPreview = useMemo(() => {
    if (!isConditionBuilderComplete(ruleForm)) {
      return ''
    }

    return formatConditionPreview(
      buildConditionObject(ruleForm, conditionFields),
      ruleForm.condition_match,
    )
  }, [conditionFields, ruleForm])

  function updateConditionRow(index, patch) {
    setRuleForm((current) => ({
      ...current,
      conditions: current.conditions.map((condition, conditionIndex) => {
        if (conditionIndex !== index) {
          return condition
        }

        const nextCondition = { ...condition, ...patch }
        if (Object.prototype.hasOwnProperty.call(patch, 'field')) {
          const nextField = conditionFields.find((field) => field.key === patch.field)
          return {
            ...nextCondition,
            operator: normalizeOperator(nextField, nextCondition.operator),
            value: defaultValueForField(nextField),
          }
        }

        return nextCondition
      }),
    }))
  }

  function addConditionRow() {
    setRuleForm((current) => ({
      ...current,
      conditions: [...current.conditions, emptyConditionRow],
    }))
  }

  function removeConditionRow(index) {
    setRuleForm((current) => ({
      ...current,
      conditions:
        current.conditions.length > 1
          ? current.conditions.filter((_, conditionIndex) => conditionIndex !== index)
          : current.conditions,
    }))
  }

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
      const condition = buildConditionObject(ruleForm, conditionFields)
      await createSymptomRule({
        stage: Number(ruleForm.stage),
        name: ruleForm.name,
        condition,
        risk_level: ruleForm.risk_level,
        recommended_action: ruleForm.recommended_action,
        appointment_priority: ruleForm.appointment_priority,
        explanation: ruleForm.explanation,
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

        <Section className="model-builder-panel" title="Symptoms">
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
            className="scrollable-resource-list"
            items={symptoms}
            getText={(symptom) => `${symptom.label} (${symptom.key}) - ${formatConstant(symptom.data_type)}`}
          />
        </Section>

        <Section className="model-builder-panel" title="Symptom Rules">
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
            <ConditionBuilder
              conditionFields={conditionFields}
              disabled={isActive}
              matchMode={ruleForm.condition_match}
              onAddCondition={addConditionRow}
              onMatchModeChange={(value) =>
                setRuleForm((current) => ({ ...current, condition_match: value }))
              }
              onRemoveCondition={removeConditionRow}
              onUpdateCondition={updateConditionRow}
              preview={conditionPreview}
              rows={ruleForm.conditions}
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
            <label>
              Rule appointment priority
              <select
                value={ruleForm.appointment_priority}
                onChange={(event) =>
                  setRuleForm((current) => ({
                    ...current,
                    appointment_priority: event.target.value,
                  }))
                }
              >
                <option value="NONE">None</option>
                <option value="LOW">Low</option>
                <option value="NORMAL">Normal</option>
                <option value="HIGH">High</option>
                <option value="URGENT">Urgent</option>
              </select>
              <small className="muted-text">
                Used on the risk assessment if this rule wins. Staff escalation priority is set
                separately below.
              </small>
            </label>
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
            className="scrollable-resource-list"
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

        <Section className="support-builder-panel" title="AI Constraints">
          {isActive ? <ActiveWorkflowNotice /> : null}
          <form className="panel-form compact-form" onSubmit={submitBoundary}>
            <p className="muted-text">
              Add at least one workflow-level boundary that allows aftercare guidance but forbids
              diagnosis and prescription.
            </p>
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
            className="scrollable-resource-list"
            items={boundaries}
            getText={(boundary) =>
              `Boundary ${boundary.id}: forbids ${(boundary.forbidden_topics || [])
                .map(formatConstant)
                .join(', ')}`
            }
          />
        </Section>

        <Section className="support-builder-panel" title="Staff Escalation Rules">
          {isActive ? <ActiveWorkflowNotice /> : null}
          <form className="panel-form compact-form" onSubmit={submitEscalation}>
            <p className="muted-text">
              Create one staff escalation for every HIGH or URGENT symptom rule.
            </p>
            <select
              required
              value={escalationForm.symptom_rule}
              onChange={(event) => {
                const selectedRule = escalationRuleOptions.find(
                  (rule) => String(rule.value) === event.target.value,
                )
                setEscalationForm((current) => ({
                  ...current,
                  appointment_priority: selectedRule?.appointmentPriority || current.appointment_priority,
                  message:
                    current.message ||
                    (selectedRule ? `Staff review required for ${selectedRule.label}.` : ''),
                  symptom_rule: event.target.value,
                  urgency: selectedRule?.riskLevel || current.urgency,
                }))
              }}
            >
              <option value="">Select HIGH/URGENT rule needing escalation</option>
              {escalationRuleOptions.map((rule) => (
                <option key={rule.value} value={rule.value}>
                  {rule.label}
                </option>
              ))}
            </select>
            <div className="inline-fields">
              <label>
                Staff review urgency
                <select
                  value={escalationForm.urgency}
                  onChange={(event) =>
                    setEscalationForm((current) => ({ ...current, urgency: event.target.value }))
                  }
                >
                  <option value="HIGH">High</option>
                  <option value="URGENT">Urgent</option>
                </select>
                <small className="muted-text">
                  Staff review urgency controls escalation queue severity.
                </small>
              </label>
              <label>
                Appointment priority
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
                <small className="muted-text">
                  Appointment priority controls scheduling priority if an appointment is created.
                </small>
              </label>
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
            className="scrollable-resource-list"
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

function ResourceList({ className = '', items, getText, renderItem }) {
  if (items.length === 0) {
    return <p className="muted-text">None yet.</p>
  }

  return (
    <ul className={`resource-list compact-list ${className}`.trim()}>
      {items.map((item) => (
        <li key={item.id}>
          {renderItem ? renderItem(item) : <span>{getText(item)}</span>}
        </li>
      ))}
    </ul>
  )
}

function ConditionBuilder({
  conditionFields,
  disabled,
  matchMode,
  onAddCondition,
  onMatchModeChange,
  onRemoveCondition,
  onUpdateCondition,
  preview,
  rows,
}) {
  return (
    <div className="condition-builder">
      <label>
        Rule matching
        <select
          disabled={disabled}
          value={matchMode}
          onChange={(event) => onMatchModeChange(event.target.value)}
        >
          <option value="all">Match all conditions</option>
          <option value="any">Match any condition</option>
        </select>
        <small className="muted-text">
          {matchMode === 'all'
            ? 'All rows must be true for the same patient report. A range like pain >= 5 and pain < 8 means 5 <= pain < 8.'
            : 'At least one row must be true for the rule to match.'}
        </small>
      </label>

      <div className="condition-row-list">
        {rows.map((row, index) => (
          <ConditionRow
            conditionFields={conditionFields}
            disabled={disabled}
            index={index}
            key={index}
            onRemove={onRemoveCondition}
            onUpdate={onUpdateCondition}
            row={withFieldDefinition(row, conditionFields)}
            showRemove={rows.length > 1}
          />
        ))}
      </div>

      <button
        className="secondary-button"
        disabled={disabled}
        type="button"
        onClick={onAddCondition}
      >
        Add condition
      </button>

      <small className="muted-text">
        Condition preview:{' '}
        {preview || 'Select fields to preview the generated rule condition.'}
      </small>
    </div>
  )
}

function ConditionRow({
  conditionFields,
  disabled,
  index,
  onRemove,
  onUpdate,
  row,
  showRemove,
}) {
  const operators = operatorsForField(row.fieldDefinition)

  return (
    <div className="condition-row inline-fields">
      <select
        disabled={disabled}
        required
        value={row.field}
        onChange={(event) => onUpdate(index, { field: event.target.value })}
      >
        <option value="">Select field</option>
        {conditionFields.map((field) => (
          <option key={field.key} value={field.key}>
            {conditionFieldLabel(field)}
          </option>
        ))}
      </select>

      <select
        disabled={disabled}
        required
        value={row.operator}
        onChange={(event) => onUpdate(index, { operator: event.target.value })}
      >
        {operators.map((operator) => (
          <option key={operator} value={operator}>
            {operator}
          </option>
        ))}
      </select>

      <ConditionValueInput
        disabled={disabled}
        field={row.fieldDefinition}
        onChange={(value) => onUpdate(index, { value })}
        value={row.value}
      />

      <button
        className="secondary-button"
        disabled={disabled || !showRemove}
        type="button"
        onClick={() => onRemove(index)}
      >
        Remove
      </button>
    </div>
  )
}

function ConditionValueInput({ disabled, field, onChange, value }) {
  if (field?.data_type === 'BOOLEAN') {
    return (
      <select
        disabled={disabled}
        required
        value={String(value)}
        onChange={(event) => onChange(event.target.value === 'true')}
      >
        <option value="true">Yes</option>
        <option value="false">No</option>
      </select>
    )
  }

  if (field?.data_type === 'CHOICE') {
    const choices = choiceValuesForField(field)
    if (choices.length) {
      return (
        <select
          disabled={disabled}
          required
          value={value}
          onChange={(event) => onChange(event.target.value)}
        >
          {choices.map((choice) => (
            <option key={choice} value={choice}>
              {formatConstant(choice)}
            </option>
          ))}
        </select>
      )
    }
  }

  if (field?.data_type === 'INTEGER') {
    return (
      <input
        disabled={disabled}
        max={field.max_value ?? undefined}
        min={field.min_value ?? undefined}
        required
        type="number"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
    )
  }

  return (
    <input
      disabled={disabled}
      placeholder="Value"
      required
      type="text"
      value={value}
      onChange={(event) => onChange(event.target.value)}
    />
  )
}
