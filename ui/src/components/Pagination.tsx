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
  totalPages?: number;
}

const Pagination: React.FC<PaginationProps> = ({
  currentPage,
  canGoPrev,
  canGoNext,
  onPrev,
  onNext,
  summaryText,
  className = "",
  totalPages,
}) => {
  return (
    <div className={cn("flex items-center justify-between px-2 py-1", className)}>
      <div className="text-xs text-gray-600">
        {summaryText || null}
      </div>

      <div className="flex items-center space-x-1">
        <button
          onClick={onPrev}
          disabled={!canGoPrev}
          className={cn(
            "w-6 h-6 flex items-center justify-center rounded text-sm font-medium transition-colors",
            canGoPrev
              ? "text-gray-400 hover:text-gray-200"
              : "text-gray-700 cursor-not-allowed"
          )}
          title="Previous page"
        >
          &lt;
        </button>

        <span className="text-sm text-gray-500 px-1">
          {totalPages ? `${currentPage}/${totalPages}` : currentPage}
        </span>

        <button
          onClick={onNext}
          disabled={!canGoNext}
          className={cn(
            "w-6 h-6 flex items-center justify-center rounded text-sm font-medium transition-colors",
            canGoNext
              ? "text-gray-400 hover:text-gray-200"
              : "text-gray-700 cursor-not-allowed"
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

