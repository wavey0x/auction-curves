import { useState, useRef, useEffect } from 'react';

export interface TooltipPosition {
  x: number;
  y: number;
}

export interface HoverTooltipOptions {
  enabled?: boolean;
  hoverDelay?: number;
}

export interface HoverTooltipReturn {
  isHovered: boolean;
  tooltipPosition: TooltipPosition;
  containerRef: React.RefObject<HTMLDivElement>;
  handleMouseEnter: () => void;
  handleMouseLeave: () => void;
  handleTooltipMouseEnter: () => void;
  handleTooltipMouseLeave: () => void;
}

/**
 * Reusable hook for portal-based hover tooltips
 * Extracted from InternalLink component for consistent UX across components
 */
export const useHoverTooltip = (options: HoverTooltipOptions = {}): HoverTooltipReturn => {
  const { enabled = true, hoverDelay = 100 } = options;
  
  const [isHovered, setIsHovered] = useState(false);
  const [tooltipPosition, setTooltipPosition] = useState<TooltipPosition>({ x: 0, y: 0 });
  const containerRef = useRef<HTMLDivElement>(null);
  const hoverTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const updateTooltipPosition = () => {
    if (containerRef.current) {
      const rect = containerRef.current.getBoundingClientRect();
      setTooltipPosition({
        x: rect.left + rect.width / 2,
        y: rect.bottom + 4
      });
    }
  };

  const handleMouseEnter = () => {
    if (enabled) {
      if (hoverTimeoutRef.current) {
        clearTimeout(hoverTimeoutRef.current);
        hoverTimeoutRef.current = null;
      }
      setIsHovered(true);
      updateTooltipPosition();
    }
  };

  const handleMouseLeave = () => {
    if (enabled) {
      // Add a small delay before hiding to allow cursor movement to tooltip
      hoverTimeoutRef.current = setTimeout(() => {
        setIsHovered(false);
      }, hoverDelay);
    }
  };

  const handleTooltipMouseEnter = () => {
    // Cancel the hide timeout if cursor enters tooltip
    if (hoverTimeoutRef.current) {
      clearTimeout(hoverTimeoutRef.current);
      hoverTimeoutRef.current = null;
    }
  };

  const handleTooltipMouseLeave = () => {
    // Hide immediately when leaving tooltip
    setIsHovered(false);
  };

  useEffect(() => {
    if (isHovered) {
      const handleScroll = () => updateTooltipPosition();
      window.addEventListener('scroll', handleScroll, true);
      window.addEventListener('resize', handleScroll);
      return () => {
        window.removeEventListener('scroll', handleScroll, true);
        window.removeEventListener('resize', handleScroll);
      };
    }
  }, [isHovered]);

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (hoverTimeoutRef.current) {
        clearTimeout(hoverTimeoutRef.current);
      }
    };
  }, []);

  return {
    isHovered,
    tooltipPosition,
    containerRef,
    handleMouseEnter,
    handleMouseLeave,
    handleTooltipMouseEnter,
    handleTooltipMouseLeave,
  };
};