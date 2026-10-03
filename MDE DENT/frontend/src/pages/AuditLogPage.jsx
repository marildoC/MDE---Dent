import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  askAdminIntelligence,
  listAdminIntelligenceSuggestions,
} from '../api/adminIntelligence.js'
import { useAuth } from '../auth/useAuth.js'
import { formatConstant, formatDateTime } from '../utils/display.js'

const defaultSuggestions = [
  'How many appointments are scheduled today?',
  'Show unresolved urgent escalations',
  'Show active workflows',
  'Show recent audit events',
  'Show appointment-required cases without scheduled appointment',
]

function historyKey(userId) {
  return `dentcare_admin_intelligence_${userId}`
}

function makeId() {
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`
}

export default function AuditLogPage() {
  const { logout, user } = useAuth()
  const [question, setQuestion] = useState('')
  const [messages, setMessages] = useState(() => loadHistory(user?.id))
  const [suggestions, setSuggestions] = useState(defaultSuggestions)
  const [isAsking, setIsAsking] = useState(false)
  const [error, setError] = useState('')
  const chatEndRef = useRef(null)
  const storageKey = user?.id ? historyKey(user.id) : ''

  useEffect(() => {
    if (!storageKey) {
      return
    }
    localStorage.setItem(storageKey, JSON.stringify(messages))
  }, [messages, storageKey])

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ block: 'end' })
  }, [messages, isAsking])

  useEffect(() => {
    let isMounted = true
    const timeoutId = window.setTimeout(() => {
      listAdminIntelligenceSuggestions(question.trim())
        .then((data) => {
          if (isMounted) {
            setSuggestions(data.suggestions || defaultSuggestions)
          }
        })
        .catch(() => {
          if (isMounted) {
            setSuggestions(defaultSuggestions)
          }
        })
    }, 180)

    return () => {
      isMounted = false
      window.clearTimeout(timeoutId)
    }
  }, [question])

  const submitQuestion = async (value = question) => {
    const trimmed = value.trim()
    if (!trimmed || isAsking) {
      return
    }

    setQuestion('')
    setError('')
    setIsAsking(true)
    setMessages((current) => [
      ...current,
      {
        content: trimmed,
        id: makeId(),
        role: 'user',
      },
    ])

    try {
      const result = await askAdminIntelligence(trimmed)
      setMessages((current) => [
        ...current,
        {
          id: makeId(),
          result,
          role: 'assistant',
        },
      ])
      if (result.suggested_followups?.length) {
        setSuggestions(result.suggested_followups)
      }
    } catch (err) {
      setError(err.message)
      setMessages((current) => [
        ...current,
        {
          content: 'Admin Intelligence could not answer that request right now.',
          id: makeId(),
          role: 'assistant',
        },
      ])
    } finally {
      setIsAsking(false)
    }
  }

  const handleSubmit = (event) => {
    event.preventDefault()
    submitQuestion()
  }

  const handleQuestionKeyDown = (event) => {
    if (event.key !== 'Enter' || event.shiftKey) {
      return
    }
    event.preventDefault()
    submitQuestion()
  }

  const handleLogout = () => {
    if (storageKey) {
      localStorage.removeItem(storageKey)
    }
    logout()
  }

  return (
    <main className="app-shell">
      <header className="top-bar admin-intelligence-topbar">
        <div>
          <p className="eyebrow">Admin area</p>
          <h1>Admin Intelligence</h1>
          <p className="muted-text">Welcome, {user?.username || 'admin'}</p>
        </div>
        <div className="button-row">
          <Link className="secondary-link" to="/admin">
            Dashboard
          </Link>
          <button className="secondary-button" type="button" onClick={handleLogout}>
            Logout
          </button>
        </div>
      </header>

      <section className="dashboard-panel admin-intelligence-panel">
        <div className="chat-history">
          {messages.length === 0 ? (
            <div className="empty-chat-state">
              <h3>Ask a question to begin.</h3>
              <p className="muted-text">
                Admin Intelligence returns grounded answers from existing records without changing
                patient, workflow, escalation, appointment, or audit data.
              </p>
            </div>
          ) : null}
          {messages.map((message) => (
            <ChatMessage key={message.id} message={message} onSuggestionClick={submitQuestion} />
          ))}
          {isAsking ? (
            <div className="chat-message assistant-message">
              <p className="message-author">Admin Intelligence</p>
              <p className="muted-text">Analyzing system data...</p>
            </div>
          ) : null}
          <div ref={chatEndRef} />
        </div>

        <div className="intelligence-composer">
          {error ? <p className="form-error">{error}</p> : null}
          <div className="suggestion-strip" aria-label="Suggested questions">
            {suggestions.map((suggestion) => (
              <button
                className="suggestion-chip"
                disabled={isAsking}
                key={suggestion}
                onClick={() => submitQuestion(suggestion)}
                type="button"
              >
                {suggestion}
              </button>
            ))}
          </div>

          <form className="intelligence-query-box" onSubmit={handleSubmit}>
            <label>
              <span className="sr-only">Question</span>
              <textarea
                onChange={(event) => setQuestion(event.target.value)}
                onKeyDown={handleQuestionKeyDown}
                placeholder="Ask about patients, cases, appointments, escalations, workflows, or audit history..."
                rows="1"
                value={question}
              />
            </label>
            <button className="primary-button" disabled={isAsking || !question.trim()} type="submit">
              {isAsking ? 'Analyzing...' : 'Ask'}
            </button>
          </form>
        </div>
      </section>
    </main>
  )
}

function loadHistory(userId) {
  if (!userId) {
    return []
  }

  try {
    const value = localStorage.getItem(historyKey(userId))
    return value ? JSON.parse(value) : []
  } catch {
    return []
  }
}

function ChatMessage({ message, onSuggestionClick }) {
  if (message.role === 'user') {
    return (
      <div className="chat-message user-message">
        <p className="message-author">You</p>
        <p>{message.content}</p>
      </div>
    )
  }

  return (
    <div className="chat-message assistant-message">
      <p className="message-author">Admin Intelligence</p>
      {message.result ? (
        <StructuredAnswer result={message.result} onSuggestionClick={onSuggestionClick} />
      ) : (
        <p>{message.content}</p>
      )}
    </div>
  )
}

function StructuredAnswer({ result, onSuggestionClick }) {
  return (
    <div className="structured-answer">
      <p>{result.answer}</p>
      {result.display_type === 'unsupported' && result.data?.scope ? (
        <small className="muted-text">{result.data.scope}</small>
      ) : null}
      {result.display_type === 'table' ? <AnswerTable columns={result.columns} rows={result.rows} /> : null}
      {result.display_type === 'cards' ? <AnswerCards cards={result.cards} /> : null}
      {result.display_type === 'timeline' ? <AnswerTimeline items={result.timeline} /> : null}
      {result.evidence?.length ? <EvidenceList evidence={result.evidence} /> : null}
      {result.suggested_followups?.length ? (
        <div className="answer-followups" aria-label="Suggested follow-up questions">
          {result.suggested_followups.map((suggestion) => (
            <button
              className="suggestion-chip"
              key={suggestion}
              onClick={() => onSuggestionClick(suggestion)}
              type="button"
            >
              {suggestion}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  )
}

function AnswerTable({ columns = [], rows = [] }) {
  if (!rows.length) {
    return null
  }

  return (
    <div className="answer-table-wrap">
      <table className="answer-table">
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column.key}>{column.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={row.id || index}>
              {columns.map((column) => (
                <td key={column.key}>{formatAnswerValue(column.key, row[column.key])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function AnswerCards({ cards = [] }) {
  if (!cards.length) {
    return null
  }

  return (
    <div className="answer-card-grid">
      {cards.map((card) => (
        <article className="answer-card" key={card.title}>
          <h3>{card.title}</h3>
          <dl>
            {card.fields.map((field) => (
              <div key={`${card.title}-${field.label}`}>
                <dt>{field.label}</dt>
                <dd>{formatAnswerValue(field.label, field.value)}</dd>
              </div>
            ))}
          </dl>
        </article>
      ))}
    </div>
  )
}

function AnswerTimeline({ items = [] }) {
  if (!items.length) {
    return null
  }

  return (
    <ol className="answer-timeline">
      {items.map((item) => (
        <li key={item.id}>
          <span className="timeline-marker" />
          <div>
            <strong>{formatConstant(item.action)}</strong>
            <small>{formatDateTime(item.timestamp)}</small>
            <small>
              Actor: {item.actor} | Target: {item.target}
            </small>
            {item.summary ? <small>{item.summary}</small> : null}
          </div>
        </li>
      ))}
    </ol>
  )
}

function EvidenceList({ evidence = [] }) {
  return (
    <div className="evidence-list" aria-label="Evidence references">
      {evidence.map((item) => (
        <span key={`${item.type}-${item.id}`}>
          {item.type} #{item.id}
        </span>
      ))}
    </div>
  )
}

function formatAnswerValue(key, value) {
  if (value === null || value === undefined || value === '') {
    return 'Unavailable'
  }

  const normalizedKey = String(key).toLowerCase()
  if (normalizedKey.includes('time') || normalizedKey.includes('date') || normalizedKey.includes('at')) {
    return formatDateTime(value)
  }
  if (
    normalizedKey.includes('status') ||
    normalizedKey.includes('risk') ||
    normalizedKey.includes('priority') ||
    normalizedKey.includes('action') ||
    normalizedKey.includes('type')
  ) {
    return formatConstant(value)
  }
  return String(value)
}
