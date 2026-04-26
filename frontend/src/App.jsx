import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import './App.css'
import { AuthProvider } from './auth/AuthContext.jsx'
import AppErrorBoundary from './components/AppErrorBoundary.jsx'
import ProtectedRoute from './components/ProtectedRoute.jsx'
import LoginPage from './pages/LoginPage.jsx'
import {
  AdminDashboard,
  PatientDashboard,
  StaffDashboard,
} from './pages/Dashboards.jsx'
import FollowUpManagementPage from './pages/FollowUpManagementPage.jsx'
import WorkflowDetailPage from './pages/WorkflowDetailPage.jsx'
import WorkflowListPage from './pages/WorkflowListPage.jsx'

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
    <AppErrorBoundary>
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
            <Route
              path="/admin/workflows"
              element={
                <ProtectedRoute allowedRoles={['ADMIN']}>
                  <WorkflowListPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin/workflows/:workflowId"
              element={
                <ProtectedRoute allowedRoles={['ADMIN']}>
                  <WorkflowDetailPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/follow-up-cases"
              element={
                <ProtectedRoute allowedRoles={['DENTIST', 'ADMIN']}>
                  <FollowUpManagementPage />
                </ProtectedRoute>
              }
            />
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </AppErrorBoundary>
  )
}

export default App
