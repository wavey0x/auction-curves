import React, { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { Gavel, Activity, TrendingUp, Settings, Book } from 'lucide-react'
import SettingsModal from './SettingsModal'
import { useUserSettings } from '../context/UserSettingsContext'

interface LayoutProps {
  children: React.ReactNode
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const location = useLocation()

  const navigation = []

  const [settingsOpen, setSettingsOpen] = useState(false)
  const { customRpcWarning, dismissCustomRpcWarning, disableCustomRpc } = useUserSettings()

  return (
    <div className="min-h-screen bg-gray-950 flex flex-col">
      {/* Header */}
      <header className="border-b border-gray-800 bg-gray-900/50 backdrop-blur-xl sticky top-0 z-50">
        <div className="px-6 lg:px-8">
          <div className="flex h-16 items-center justify-between">
            {/* Logo */}
            <div className="flex items-center space-x-4">
              <Link to="/" className="flex items-center space-x-3 group">
                <div className="relative">
                  <div className="relative h-11 w-11 rounded-2xl p-[1px] bg-gradient-to-br from-primary-400/60 via-primary-400/0 to-primary-400/60">
                    <div className="h-full w-full rounded-2xl bg-gray-900/90 border border-primary-500/30 shadow-[0_0_24px_rgba(59,130,246,0.18)] flex items-center justify-center transition-transform duration-150 group-hover:scale-105">
                      <Gavel className="h-5 w-5 text-primary-400" />
                    </div>
                  </div>
                </div>
                <div>
                  <h1 className="text-[22px] sm:text-2xl font-black tracking-tight leading-none">
                    <span className="text-gray-100">Auction </span>
                    <span className="relative inline-block">
                      <span className="bg-gradient-to-r from-primary-300 via-primary-400 to-primary-300 bg-clip-text text-transparent">Analytics</span>
                      <span className="absolute left-0 -bottom-1 h-[2px] w-full bg-gradient-to-r from-primary-500/0 via-primary-500/60 to-primary-500/0" />
                    </span>
                  </h1>
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
            <div className="flex items-center">
              <button onClick={() => setSettingsOpen(true)} className="p-2 text-gray-400 hover:text-gray-200 hover:bg-gray-800/50 rounded-lg transition-colors" aria-label="Open settings">
                <Settings className="h-5 w-5" />
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Warning banner for custom RPC issues */}
      {customRpcWarning.visible && (
        <div className="px-6 lg:px-8 mt-2">
          <div className="flex items-start justify-between rounded-lg border border-yellow-700 bg-yellow-900/30 text-yellow-200 p-3">
            <div className="text-sm">
              <span className="font-medium">Custom RPC issue:</span> {customRpcWarning.message || 'The configured RPC appears to be failing.'}
            </div>
            <div className="flex items-center gap-2">
              <button onClick={disableCustomRpc} className="text-xs px-2 py-1 rounded bg-yellow-700/30 hover:bg-yellow-700/40 border border-yellow-700">Disable custom RPC</button>
              <button onClick={dismissCustomRpcWarning} className="text-xs px-2 py-1 rounded hover:bg-yellow-700/20">Dismiss</button>
            </div>
          </div>
        </div>
      )}

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
            
            <span className="mx-3">|</span>
            
            <Link 
              to="/api-docs" 
              className="flex items-center space-x-1 hover:text-gray-300 transition-colors"
            >
              <Book className="h-3 w-3" />
              <span>API Docs</span>
            </Link>
          </div>
        </div>
      </footer>

      {/* Settings Modal */}
      <SettingsModal open={settingsOpen} onClose={() => setSettingsOpen(false)} />
    </div>
  )
}

export default Layout
