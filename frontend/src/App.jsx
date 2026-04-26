import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import './App.css'
import { AuthProvider } from './auth/AuthContext.jsx'
import ProtectedRoute from './components/ProtectedRoute.jsx'
import LoginPage from './pages/LoginPage.jsx'
import {
  AdminDashboard,
  PatientDashboard,
  StaffDashboard,
} from './pages/Dashboards.jsx'

function RoleRedirect() {
  return (
    <ProtectedRoute>
      {({ user }) => {
        if (user.role === 'ADMIN') {
          return <Navigate to="/admin" replace />
        }

        if (user.role === 'DENTIST') {
          return <Navigate to="/staff" replace />
        }

        return <Navigate to="/patient" replace />
      }}
    </ProtectedRoute>
  )
}

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<RoleRedirect />} />
          <Route
            path="/patient"
            element={
              <ProtectedRoute allowedRoles={['PATIENT']}>
                <PatientDashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/staff"
            element={
              <ProtectedRoute allowedRoles={['DENTIST', 'ADMIN']}>
                <StaffDashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin"
            element={
              <ProtectedRoute allowedRoles={['ADMIN']}>
                <AdminDashboard />
              </ProtectedRoute>
            }
          />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}

export default App
