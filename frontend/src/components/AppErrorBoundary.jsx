import { Component } from 'react'

export default class AppErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError() {
    return { hasError: true }
  }

  componentDidCatch(error) {
    console.error('Application render error:', error)
  }

  render() {
    if (this.state.hasError) {
      return (
        <main className="app-shell">
          <section className="status-panel">
            <h1>Something went wrong</h1>
            <p>Sign out and sign in again, or refresh after the server finishes loading.</p>
            <button
              className="primary-button"
              type="button"
              onClick={() => {
                localStorage.removeItem('dentcare_access_token')
                localStorage.removeItem('dentcare_refresh_token')
                window.location.assign('/login')
              }}
            >
              Go to login
            </button>
          </section>
        </main>
      )
    }

    return this.props.children
  }
}
