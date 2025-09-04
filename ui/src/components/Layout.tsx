import React, { useState, useEffect } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { Gavel, Activity, TrendingUp, Settings, Book } from 'lucide-react'
import SettingsModal from './SettingsModal'
import NotificationContainer from './NotificationContainer'
import { useUserSettings } from '../context/UserSettingsContext'
import { useNotifications } from '../context/NotificationContext'
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../lib/api'
import { eventStreamService } from '../services/eventStreamService'

interface LayoutProps {
  children: React.ReactNode
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const location = useLocation()

  const navigation = []

  const [settingsOpen, setSettingsOpen] = useState(false)
  const { customRpcWarning, dismissCustomRpcWarning, disableCustomRpc } = useUserSettings()
  const { addNotification } = useNotifications()

  // Persist settings modal open state to survive refresh/HMR
  React.useEffect(() => {
    try {
      const raw = localStorage.getItem('settings_modal_open')
      if (raw === 'true') setSettingsOpen(true)
    } catch {}
    // run once
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  React.useEffect(() => {
    try { localStorage.setItem('settings_modal_open', settingsOpen ? 'true' : 'false') } catch {}
  }, [settingsOpen])

  // Initialize event stream for real-time notifications
  useEffect(() => {
    const unsubscribe = eventStreamService.addListener((notification) => {
      addNotification(notification)
    })

    eventStreamService.connect()

    return () => {
      unsubscribe()
      eventStreamService.disconnect()
    }
  }, [addNotification])

  const { data: statusData, error: statusError, isLoading } = useQuery({
    queryKey: ['status-summary'],
    queryFn: () => apiClient.getStatus(),
    refetchInterval: 5000, // More aggressive refresh - every 5 seconds
    staleTime: 0, // Always consider data stale for immediate updates
    retry: 3,
  })


  let healthLabel = 'Healthy'
  let healthColor = 'text-green-400'
  let healthBg = 'bg-green-400'
  
  if (isLoading && !statusData) {
    healthLabel = 'Loading'
    healthColor = 'text-gray-400'
    healthBg = 'bg-gray-400'
  } else if (statusError || !statusData) {
    healthLabel = 'Unhealthy'
    healthColor = 'text-red-400'
    healthBg = 'bg-red-400'
  } else {
    const services = statusData.services || []
    const anyDown = services.some((s: any) => s.status === 'down')
    const anyWarn = services.some((s: any) => s.status === 'degraded' || s.status === 'unknown')
    if (anyDown) { healthLabel = 'Unhealthy'; healthColor = 'text-red-400'; healthBg = 'bg-red-400' }
    else if (anyWarn) { healthLabel = 'Degraded'; healthColor = 'text-yellow-400'; healthBg = 'bg-yellow-400' }
    else { healthLabel = 'Healthy'; healthColor = 'text-green-400'; healthBg = 'bg-green-400' }
  }

  return (
    <div className="min-h-screen bg-gray-950 flex flex-col">
      {/* Header */}
      <header className="border-b border-gray-800 bg-gray-900/50 backdrop-blur-xl sticky top-0 z-50">
        <div className="px-6 lg:px-8">
          <div className="flex h-16 items-center justify-between">
            {/* Logo */}
            <div className="flex items-center space-x-4">
              <Link to="/" className="flex items-center space-x-3 group">
                <div className="h-11 w-11 pixel-badge rounded-none">
                  <Gavel className="h-5 w-5 text-primary-300" />
                </div>
                <div>
                  <h1 className="logo-8bit glow-text text-[20px] sm:text-[22px] font-black leading-none text-primary-300">
                    [ AUCTION <span className="text-gray-200">ANALYTICS</span> ]
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
            <Link to="/status" className={`flex items-center gap-2 font-semibold ${healthColor} hover:opacity-90`}>
              <span className="relative inline-flex">
                <span className={`absolute inline-flex h-2 w-2 rounded-full ${healthBg} opacity-50 animate-ping`}></span>
                <span className={`relative inline-flex h-2 w-2 rounded-full ${healthBg}`}></span>
              </span>
              <span>{healthLabel}</span>
            </Link>

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
      
      {/* Notification Container */}
      <NotificationContainer />
    </div>
  )
}

export default Layout
