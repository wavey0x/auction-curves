import React, { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { Gavel, Activity, TrendingUp, Settings } from 'lucide-react'
import SettingsModal from './SettingsModal'

interface LayoutProps {
  children: React.ReactNode
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const location = useLocation()

  const navigation = [
    // Add more nav items as needed
  ]

  const [settingsOpen, setSettingsOpen] = useState(false)

  return (
    <div className="min-h-screen bg-gray-950 flex flex-col">
      {/* Header */}
      <header className="border-b border-gray-800 bg-gray-900/50 backdrop-blur-xl sticky top-0 z-50">
        <div className="px-6 lg:px-8">
          <div className="flex h-16 items-center justify-between">
            {/* Logo */}
            <div className="flex items-center space-x-4">
              <Link to="/" className="flex items-center space-x-3 group">
                <div className="p-2 bg-primary-500/10 rounded-lg group-hover:bg-primary-500/20 transition-colors">
                  <Gavel className="h-6 w-6 text-primary-400" />
                </div>
                <div>
                  <h1 className="text-xl font-bold text-gradient">
                    Auction House
                  </h1>
                  <p className="text-xs text-gray-500">Monitoring</p>
                </div>
              </Link>
            </div>

            {/* Navigation */}
            <nav className="hidden md:flex items-center space-x-6">
              {navigation.map((item) => {
                const Icon = item.icon
                return (
                  <Link
                    key={item.name}
                    to={item.href}
                    className={`flex items-center space-x-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                      item.current
                        ? 'bg-primary-500/20 text-primary-400'
                        : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800/50'
                    }`}
                  >
                    <Icon className="h-4 w-4" />
                    <span>{item.name}</span>
                  </Link>
                )
              })}
            </nav>

            {/* Right side */}
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-2 text-sm">
                <div className="h-2 w-2 bg-success-500 rounded-full animate-pulse"></div>
                <span className="text-gray-400">Live</span>
              </div>
              
              <button onClick={() => setSettingsOpen(true)} className="p-2 text-gray-400 hover:text-gray-200 hover:bg-gray-800/50 rounded-lg transition-colors" aria-label="Open settings">
                <Settings className="h-5 w-5" />
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1">
        <div className="px-6 py-8 pb-12 lg:px-8">
          {children}
        </div>
      </main>

      {/* Footer */}
      <footer className="fixed bottom-0 left-0 right-0 border-t border-gray-800 bg-gray-900/80 backdrop-blur-xl py-2 z-40">
        <div className="px-6 lg:px-8">
          <div className="flex items-center justify-center text-xs text-gray-500">
            <span className="flex items-center space-x-2">
              <div className="h-1.5 w-1.5 bg-success-500 rounded-full"></div>
              <span>Live</span>
            </span>
          </div>
        </div>
      </footer>

      {/* Settings Modal */}
      <SettingsModal open={settingsOpen} onClose={() => setSettingsOpen(false)} />
    </div>
  )
}

export default Layout
