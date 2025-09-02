import React from "react";
import { LucideIcon } from "lucide-react";

interface Item {
  label: string;
  value: React.ReactNode;
  hint?: React.ReactNode;
  icon?: LucideIcon;
  expandable?: boolean;
  expandedContent?: React.ReactNode;
  isExpanded?: boolean;
}

interface KeyValueGridProps {
  items: Item[];
  columns?: 1 | 2 | 3;
  className?: string;
}

const KeyValueGrid: React.FC<KeyValueGridProps> = ({ items, columns = 2, className = "" }) => {
  const getColClass = () => {
    if (columns === 3) return "lg:grid-cols-3 md:grid-cols-2";
    if (columns === 2) return "md:grid-cols-2";
    return "md:grid-cols-1";
  };

  return (
    <div className={`grid grid-cols-1 ${getColClass()} gap-4 md:gap-6 ${className}`}>
      {items.map((it, idx) => {
        const Icon = it.icon;
        const isExpandableItem = it.expandable && it.expandedContent;
        const needsFullWidth = isExpandableItem && it.isExpanded;
        
        return (
          <div 
            key={idx} 
            className={`min-w-0 p-3 bg-gray-800/20 rounded-md border border-gray-700/30 ${
              needsFullWidth ? 'col-span-full' : ''
            }`}
          >
            <div className="flex items-center space-x-2 mb-2">
              {Icon ? <Icon className="h-4 w-4 text-gray-400" /> : null}
              <span className="text-sm text-gray-500 font-medium">{it.label}</span>
            </div>
            <div className="text-base text-gray-200 font-medium break-words">{it.value}</div>
            {it.hint ? <div className="mt-1.5 text-xs text-gray-500">{it.hint}</div> : null}
            
            {/* Expanded Content */}
            {isExpandableItem && (
              <div 
                className={`overflow-hidden transition-all duration-300 ease-in-out ${
                  it.isExpanded ? 'max-h-96 opacity-100 mt-3' : 'max-h-0 opacity-0'
                }`}
              >
                <div className="pt-3 border-t border-gray-700/30">
                  {it.expandedContent}
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};

export default KeyValueGrid;
