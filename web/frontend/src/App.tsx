import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from './contexts/AuthContext';
import Layout from './components/Layout';
import Registry from './pages/Registry';
import LibraryDetail from './pages/LibraryDetail';
import Conformance from './pages/Conformance';
import Analyzer from './pages/Analyzer';
import Drift from './pages/Drift';
import IRExplorer from './pages/IRExplorer';
import Generator from './pages/Generator';
import Libraries from './pages/Libraries';
import LibraryViewer from './pages/LibraryViewer';
import Login from './pages/Login';
import Settings from './pages/Settings';
import Organizations from './pages/Organizations';
import OrgDetail from './pages/OrgDetail';
import LLMDashboard from './pages/LLMDashboard';
import Policies from './pages/Policies';
import Approvals from './pages/Approvals';
import SecurityDashboard from './pages/SecurityDashboard';
import SetupWizard from './pages/SetupWizard';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/setup" element={<SetupWizard />} />
            <Route path="/" element={<Layout />}>
              <Route index element={<Registry />} />
              <Route path="library/:name/:version?" element={<LibraryDetail />} />
              <Route path="conformance" element={<Conformance />} />
              <Route path="analyze" element={<Analyzer />} />
              <Route path="drift" element={<Drift />} />
              <Route path="ir" element={<IRExplorer />} />
              <Route path="generate" element={<Generator />} />
              <Route path="libraries" element={<Libraries />} />
              <Route path="libraries/:id" element={<LibraryViewer />} />
              <Route path="settings/api-keys" element={<Settings />} />
              <Route path="orgs" element={<Organizations />} />
              <Route path="orgs/:slug" element={<OrgDetail />} />
              <Route path="llm" element={<LLMDashboard />} />
              <Route path="policies" element={<Policies />} />
              <Route path="approvals" element={<Approvals />} />
              <Route path="security" element={<SecurityDashboard />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
}

export default App;
