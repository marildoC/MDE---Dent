import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from 'react'
import {
  ACCESS_TOKEN_KEY,
  REFRESH_TOKEN_KEY,
  fetchCurrentUser,
  loginRequest,
} from '../api/auth.js'
import { AuthContext } from './AuthContext.js'

export function AuthProvider({ children }) {
  const [initialAccessToken] = useState(() => localStorage.getItem(ACCESS_TOKEN_KEY))
  const [user, setUser] = useState(null)
  const [isLoading, setIsLoading] = useState(Boolean(initialAccessToken))
  const [authError, setAuthError] = useState('')

  const clearSession = useCallback(() => {
    localStorage.removeItem(ACCESS_TOKEN_KEY)
    localStorage.removeItem(REFRESH_TOKEN_KEY)
    Object.keys(localStorage)
      .filter((key) => key.startsWith('dentcare_admin_intelligence_'))
      .forEach((key) => localStorage.removeItem(key))
    setUser(null)
  }, [])

  useEffect(() => {
    if (!initialAccessToken) {
      return
    }

    fetchCurrentUser(initialAccessToken)
      .then((currentUser) => {
        setUser(currentUser)
        setAuthError('')
      })
      .catch(() => {
        clearSession()
      })
      .finally(() => {
        setIsLoading(false)
      })
  }, [clearSession, initialAccessToken])

  const login = useCallback(async ({ username, password }) => {
    setAuthError('')
    const tokens = await loginRequest({ username, password })

    localStorage.setItem(ACCESS_TOKEN_KEY, tokens.access)
    localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh)

    const currentUser = await fetchCurrentUser(tokens.access)
    setUser(currentUser)
    return currentUser
  }, [])

  const logout = useCallback(() => {
    clearSession()
  }, [clearSession])

  const value = useMemo(
    () => ({
      authError,
      isAuthenticated: Boolean(user),
      isLoading,
      login,
      logout,
      setAuthError,
      user,
    }),
    [authError, isLoading, login, logout, user],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
