import React from 'react'
import { createPortal } from 'react-dom'
import { AnimatePresence } from 'framer-motion'
import { useNotifications } from '../context/NotificationContext'
import NotificationBubble from './NotificationBubble'

const NotificationContainer: React.FC = () => {
  const { notifications, removeNotification } = useNotifications()

  // Limit to 5 visible notifications maximum
  const visibleNotifications = notifications.slice(0, 5)

  return createPortal(
    <div className="fixed top-4 right-4 z-50 pointer-events-none">
      <div className="relative pointer-events-auto">
        <AnimatePresence mode="popLayout">
          {visibleNotifications.map((notification, index) => {
            // Calculate stacking offset - newer notifications on top
            const offsetX = index * 8 // 8px horizontal offset per stack
            const offsetY = index * 4 // 4px vertical offset per stack
            const scale = 1 - (index * 0.02) // Slightly smaller for stacked items
            const opacity = 1 - (index * 0.15) // Slightly more transparent for stacked items
            
            return (
              <div
                key={`notification-${notification.id}`}
                className="absolute top-0"
                style={{
                  right: offsetX,
                  top: offsetY,
                  transform: `scale(${scale})`,
                  opacity: opacity,
                  zIndex: 1000 - index,
                  transformOrigin: 'top right'
                }}
              >
                <NotificationBubble
                  key={notification.id}
                  notification={notification}
                  onDismiss={removeNotification}
                  index={index}
                />
              </div>
            )
          })}
        </AnimatePresence>
      </div>
      
      {/* Overflow indicator */}
      {notifications.length > 5 && (
        <div className="mt-2 pointer-events-auto" style={{ marginTop: `${Math.max(0, (visibleNotifications.length - 1) * 4 + 340)}px` }}>
          <div className="inline-block bg-gray-900/90 backdrop-blur-md border border-gray-700 rounded-full px-3 py-1 text-xs text-gray-400">
            +{notifications.length - 5} more
          </div>
        </div>
      )}
    </div>,
    document.body
  )
}

export default NotificationContainer