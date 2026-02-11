import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Layout from './components/Layout';
import Registry from './pages/Registry';
import LibraryDetail from './pages/LibraryDetail';
import Conformance from './pages/Conformance';
import Analyzer from './pages/Analyzer';
import Drift from './pages/Drift';

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
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Registry />} />
            <Route path="library/:name/:version?" element={<LibraryDetail />} />
            <Route path="conformance" element={<Conformance />} />
            <Route path="analyze" element={<Analyzer />} />
            <Route path="drift" element={<Drift />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
