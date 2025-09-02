import React from "react";
import { LucideIcon } from "lucide-react";

interface MetaItem {
  label: string;
  value: React.ReactNode;
  icon?: LucideIcon;
}

const MetaBadges: React.FC<{ items: MetaItem[] }> = ({ items }) => {
  return (
    <div className="flex flex-wrap gap-2">
      {items.map((it, idx) => {
        const Icon = it.icon;
        return (
          <span key={idx} className="inline-flex items-center space-x-1.5 px-2 py-1 rounded-full bg-gray-800/60 border border-gray-700 text-xs">
            {Icon ? <Icon className="h-3 w-3 text-gray-400" /> : null}
            <span className="text-gray-400">{it.label}:</span>
            <span className="text-gray-200 font-medium">{it.value}</span>
          </span>
        );
      })}
    </div>
  );
};

export default MetaBadges;

