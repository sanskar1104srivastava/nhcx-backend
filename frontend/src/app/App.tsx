import { RouterProvider, createBrowserRouter, Navigate } from 'react-router';
import { ThemeProvider } from 'next-themes';
import { Toaster } from './components/ui/sonner';
import { AuthProvider, useAuth } from '../contexts/AuthContext';
import { PatientProvider } from '../contexts/PatientContext';
import { MainLayout } from './components/layouts/MainLayout';
import { LoginPage } from './pages/LoginPage';
import { NhcxPatientsPage } from './pages/NhcxPatientsPage';
import { NhcxPage } from './pages/NhcxPage';
import { SendRequestPage } from './pages/SendRequestPage';
import { SandboxToolsPage } from './pages/SandboxToolsPage';
import { RequestLogsPage } from './pages/RequestLogsPage';
import { CallbacksPage } from './pages/CallbacksPage';
import { NotFoundPage } from './pages/NotFoundPage';

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth();
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function AppLayout() {
  return (
    <ProtectedRoute>
      <PatientProvider>
        <MainLayout />
      </PatientProvider>
    </ProtectedRoute>
  );
}

const router = createBrowserRouter([
  { path: '/login', element: <LoginPage /> },
  {
    path: '/',
    element: <AppLayout />,
    children: [
      { index: true, element: <NhcxPatientsPage /> },
      { path: 'claims', element: <NhcxPage /> },
      { path: 'send', element: <SendRequestPage /> },
      { path: 'sandbox', element: <SandboxToolsPage /> },
      { path: 'logs', element: <RequestLogsPage /> },
      { path: 'callbacks', element: <CallbacksPage /> },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
]);

export default function App() {
  return (
    <ThemeProvider attribute="class" defaultTheme="light" enableSystem={false}>
      <AuthProvider>
        <RouterProvider router={router} />
        <Toaster />
      </AuthProvider>
    </ThemeProvider>
  );
}
