import React, { useState } from 'react'
import { ChevronDown, ChevronRight, LucideIcon } from 'lucide-react'

interface CollapsibleSectionProps {
  title: string
  icon?: LucideIcon
  iconColor?: string
  badge?: string | number
  children: React.ReactNode
  defaultOpen?: boolean
  className?: string
  seamless?: boolean
}

const CollapsibleSection: React.FC<CollapsibleSectionProps> = ({
  title,
  icon: Icon,
  iconColor = "text-gray-400",
  badge,
  children,
  defaultOpen = true,
  className = "",
  seamless = false
}) => {
  const [isOpen, setIsOpen] = useState(defaultOpen)

  return (
    <div className={`${className}`}>
      {isOpen && (
        <div className="overflow-hidden rounded-lg border border-gray-800">
          {/* Header integrated as table header */}
          <div className="bg-gray-800/50 px-3 py-2 border-b border-gray-800">
            <button
              onClick={() => setIsOpen(!isOpen)}
              className="w-full flex items-center justify-center space-x-2 hover:opacity-80 transition-opacity group"
            >
              {Icon && (
                <Icon className={`h-4 w-4 ${iconColor}`} />
              )}
              <h2 className="text-base font-semibold text-gray-200 group-hover:text-gray-100">
                {title}
              </h2>
              {badge !== undefined && (
                <span className="badge badge-neutral text-xs">{badge}</span>
              )}
              <ChevronDown className="h-3 w-3 text-gray-400 group-hover:text-gray-300 ml-1" />
            </button>
          </div>
          
          {/* Content with conditional padding */}
          <div className={seamless ? "" : "px-4 py-3"}>
            {children}
          </div>
        </div>
      )}
      
      {!isOpen && (
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="w-full flex items-center justify-center p-2 bg-gray-800/30 hover:bg-gray-800/50 border border-gray-800 rounded-lg transition-colors group space-x-2"
        >
          {Icon && (
            <Icon className={`h-4 w-4 ${iconColor}`} />
          )}
          <h2 className="text-base font-semibold text-gray-200 group-hover:text-gray-100">
            {title}
          </h2>
          {badge !== undefined && (
            <span className="badge badge-neutral text-xs">{badge}</span>
          )}
          <ChevronRight className="h-3 w-3 text-gray-400 group-hover:text-gray-300 ml-1" />
        </button>
      )}
    </div>
  )
}

export default CollapsibleSection