import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from './components/ui/toaster';
import { ToastProvider } from './components/ui/toast';
import { ThemeProvider } from './components/theme-provider';
import { DockerProvider } from './contexts/DockerContext';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Dashboard } from './pages/dashboard';
import { CaseView } from './pages/case-view';
import { SimulationView } from './pages/simulation-view';
import SetupPage from './pages/setup';
import MeshPage from './pages/mesh';
import { Navbar } from './components/navbar';
import { Sidebar } from './components/Sidebar';
import * as Tooltip from '@radix-ui/react-tooltip';

// Create a client
const queryClient = new QueryClient();

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider defaultTheme="system" storageKey="foampilot-theme">
        <DockerProvider>
          <ToastProvider>
          <Tooltip.Provider>
            <Router>
              <div className="min-h-screen bg-gray-50 flex flex-col">
                {/* Navigation */}
                <nav className="bg-white shadow-sm sticky top-0 z-40">
                  <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="flex justify-between h-16">
                      <div className="flex items-center">
                        <h1 className="text-xl font-bold text-gray-900">FOAMFlask</h1>
                      </div>
                      <div className="flex items-center space-x-4">
                        <Navbar />
                      </div>
                    </div>
                  </div>
                </nav>

                {/* Main Content */}
                <div className="flex flex-1 overflow-hidden">
                  <Sidebar />
                  <main className="flex-1 overflow-y-auto focus:outline-none">
                    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
                      <Routes>
                        <Route path="/" element={<Dashboard />} />
                        <Route path="/setup" element={<SetupPage />} />
                        <Route path="/run" element={<div className="bg-white rounded-lg shadow p-6">Run Page - Coming Soon</div>} />
                        <Route path="/mesh" element={<MeshPage />} />
                        <Route path="/plots" element={<div className="bg-white rounded-lg shadow p-6">Plots Page - Coming Soon</div>} />
                        <Route path="/post" element={<div className="bg-white rounded-lg shadow p-6">Post Processing - Coming Soon</div>} />
                        <Route path="/case/:caseId" element={<CaseView />} />
                        <Route path="/simulation/:simulationId" element={<SimulationView />} />
                      </Routes>
                    </div>
                  </main>
                </div>
                
                {/* Footer */}
                <footer className="bg-white border-t border-gray-200 py-4">
                  <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <p className="text-center text-sm text-gray-500">
                      &copy; {new Date().getFullYear()} FOAMFlask. All rights reserved.
                    </p>
                  </div>
                </footer>
                
                <Toaster />
              </div>
            </Router>
          </Tooltip.Provider>
          </ToastProvider>
        </DockerProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}

export default App;
