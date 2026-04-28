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
