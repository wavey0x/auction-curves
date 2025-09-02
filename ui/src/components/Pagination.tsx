import React from "react";
import { cn } from "../lib/utils";

interface PaginationProps {
  currentPage: number;
  canGoPrev: boolean;
  canGoNext: boolean;
  onPrev: () => void;
  onNext: () => void;
  summaryText?: string;
  className?: string;
}

const Pagination: React.FC<PaginationProps> = ({
  currentPage,
  canGoPrev,
  canGoNext,
  onPrev,
  onNext,
  summaryText,
  className = "",
}) => {
  return (
    <div className={cn("flex items-center justify-between px-4 py-3 bg-gray-800/30 border-t border-gray-700/50", className)}>
      <div className="text-sm text-gray-500">
        {summaryText || null}
      </div>

      <div className="flex items-center space-x-2">
        <button
          onClick={onPrev}
          disabled={!canGoPrev}
          className={cn(
            "w-8 h-8 flex items-center justify-center rounded text-lg font-medium transition-all duration-200",
            canGoPrev
              ? "text-gray-300 hover:text-white hover:bg-gray-700"
              : "text-gray-600 cursor-not-allowed"
          )}
          title="Previous page"
        >
          &lt;
        </button>

        <span className="text-sm text-gray-400 px-2">Page {currentPage}</span>

        <button
          onClick={onNext}
          disabled={!canGoNext}
          className={cn(
            "w-8 h-8 flex items-center justify-center rounded text-lg font-medium transition-all duration-200",
            canGoNext
              ? "text-gray-300 hover:text-white hover:bg-gray-700"
              : "text-gray-600 cursor-not-allowed"
          )}
          title="Next page"
        >
          &gt;
        </button>
      </div>
    </div>
  );
};

export default Pagination;

