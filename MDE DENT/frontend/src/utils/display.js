export function formatConstant(value) {
  if (value === null || value === undefined || value === '') {
    return 'Unavailable'
  }

  return String(value)
    .toLowerCase()
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

export function formatBoolean(value) {
  return value ? 'Yes' : 'No'
}

export function formatDateTime(value) {
  if (!value) {
    return ''
  }

  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return value
  }

  return date.toLocaleString()
}

export function statusClass(value) {
  return `status-${String(value || 'unknown').toLowerCase().replaceAll('_', '-')}`
}

export function riskClass(value) {
  return `risk-${String(value || 'unknown').toLowerCase()}`
}

export function formatDetailKey(value) {
  return formatConstant(value)
}

export const legacySymptomDefinitions = [
  {
    data_type: 'INTEGER',
    key: 'pain_level',
    label: 'Pain level',
    max_value: 10,
    min_value: 0,
  },
  {
    allowed_values: ['NONE', 'MILD', 'SEVERE'],
    data_type: 'CHOICE',
    key: 'swelling',
    label: 'Swelling',
  },
  {
    allowed_values: ['NONE', 'MILD', 'SEVERE'],
    data_type: 'CHOICE',
    key: 'bleeding',
    label: 'Bleeding',
  },
  {
    data_type: 'BOOLEAN',
    key: 'fever',
    label: 'Fever',
  },
  {
    data_type: 'BOOLEAN',
    key: 'bad_smell',
    label: 'Bad smell/taste',
  },
]

export function workflowSymptomDefinitions(source) {
  const definitions = source?.workflow_symptom_definitions || []
  return definitions.length ? definitions : legacySymptomDefinitions
}

export function reportSymptomValue(report, key) {
  if (!report) {
    return undefined
  }

  if (
    report.symptom_values &&
    Object.prototype.hasOwnProperty.call(report.symptom_values, key)
  ) {
    return report.symptom_values[key]
  }

  if (Object.prototype.hasOwnProperty.call(report, key)) {
    return report[key]
  }

  return undefined
}

export function reportSymptomEntries(report, definitions) {
  const symptomDefinitions = definitions?.length ? definitions : legacySymptomDefinitions
  return symptomDefinitions.map((definition) => {
    const value = reportSymptomValue(report, definition.key)
    return {
      definition,
      formattedValue: formatSymptomValue(value, definition),
      key: definition.key,
      label: definition.label || formatDetailKey(definition.key),
      value,
    }
  })
}

export function formatSymptomValue(value, definition = {}) {
  if (value === null || value === undefined || value === '') {
    return 'Unavailable'
  }

  if (definition.data_type === 'BOOLEAN') {
    return formatBoolean(Boolean(value))
  }

  if (definition.data_type === 'CHOICE') {
    return formatConstant(value)
  }

  if (definition.data_type === 'INTEGER') {
    return String(value)
  }

  return String(value)
}

export function primaryReportSummary(report, definitions) {
  const painValue = reportSymptomValue(report, 'pain_level')
  if (painValue !== undefined && painValue !== null && painValue !== '') {
    return `Pain ${painValue}/10`
  }

  const firstAvailable = reportSymptomEntries(report, definitions).find(
    (entry) => entry.value !== undefined && entry.value !== null && entry.value !== '',
  )

  if (!firstAvailable) {
    return 'Symptoms unavailable'
  }

  return `${firstAvailable.label}: ${firstAvailable.formattedValue}`
}
