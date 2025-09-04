import React, { createContext, useContext, useState, useCallback, useEffect } from 'react'
import { Notification, NotificationContextType } from '../types/notification'

const NotificationContext = createContext<NotificationContextType | null>(null)

export const useNotifications = () => {
  const context = useContext(NotificationContext)
  if (!context) {
    throw new Error('useNotifications must be used within NotificationProvider')
  }
  return context
}

interface NotificationProviderProps {
  children: React.ReactNode
}

export const NotificationProvider: React.FC<NotificationProviderProps> = ({
  children
}) => {
  const [notifications, setNotifications] = useState<Notification[]>([])

  const addNotification = useCallback((notification: Omit<Notification, 'dismissAt'>) => {
    const newNotification: Notification = {
      ...notification,
      dismissAt: Date.now() + 10000 // 10 seconds from now
    }

    setNotifications(prev => {
      // Check for duplicate notifications by ID
      const exists = prev.some(n => n.id === newNotification.id)
      if (exists) {
        return prev
      }

      // Add new notification to the beginning
      const updated = [newNotification, ...prev]
      
      // Keep only the 10 most recent notifications in state
      return updated.slice(0, 10)
    })
  }, [])

  const removeNotification = useCallback((id: string) => {
    setNotifications(prev => prev.filter(n => n.id !== id))
  }, [])

  const clearAllNotifications = useCallback(() => {
    setNotifications([])
  }, [])

  // Auto-dismiss expired notifications
  useEffect(() => {
    const interval = setInterval(() => {
      const now = Date.now()
      setNotifications(prev => prev.filter(n => n.dismissAt > now))
    }, 1000) // Check every second

    return () => clearInterval(interval)
  }, [])

  const value: NotificationContextType = {
    notifications,
    addNotification,
    removeNotification,
    clearAllNotifications
  }

  return (
    <NotificationContext.Provider value={value}>
      {children}
    </NotificationContext.Provider>
  )
}

export default NotificationProvider