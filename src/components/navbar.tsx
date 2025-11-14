// components/navbar.tsx
import { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

type NavItem = {
  id: string;
  label: string;
  path: string;
};

export function Navbar() {
  const location = useLocation();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('setup');

  const navItems: NavItem[] = [
    { id: 'setup', label: 'Setup', path: '/setup' },
    { id: 'run', label: 'Run', path: '/run' },
    { id: 'mesh', label: 'Mesh', path: '/mesh' },
    { id: 'plots', label: 'Plots', path: '/plots' },
    { id: 'post', label: 'Post', path: '/post' },
  ];

  const switchPage = (tabId: string, path: string) => {
    setActiveTab(tabId);
    navigate(path);
  };

  // Update active tab based on current route
  const currentTab = navItems.find(item => location.pathname.startsWith(item.path))?.id || 'setup';
  if (currentTab !== activeTab) {
    setActiveTab(currentTab);
  }

  return (
    <nav className="bg-white shadow-md sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          <div className="flex items-center">
            <h1 className="text-xl font-bold text-gray-800">FOAMPilot</h1>
          </div>
          <div className="flex space-x-1">
            {navItems.map((item) => (
              <button
                key={item.id}
                onClick={() => switchPage(item.id, item.path)}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                  activeTab === item.id
                    ? 'bg-blue-500 text-white'
                    : 'text-gray-700 hover:bg-gray-100'
                }`}
              >
                {item.label}
              </button>
            ))}
          </div>
        </div>
      </div>
    </nav>
  );
}