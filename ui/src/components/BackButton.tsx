import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { useNavigation } from '../contexts/NavigationProvider';

interface BackButtonProps {
  className?: string;
  fallbackPath?: string;
  fallbackLabel?: string;
}

const BackButton: React.FC<BackButtonProps> = ({ 
  className = "btn btn-secondary btn-sm",
  fallbackPath = "/",
  fallbackLabel = "Back to Dashboard"
}) => {
  const navigate = useNavigate();
  const { canGoBack, goBack, getPreviousEntry } = useNavigation();
  
  const handleBack = (e: React.MouseEvent) => {
    e.preventDefault();
    
    if (canGoBack) {
      const previousPath = goBack();
      if (previousPath) {
        navigate(previousPath);
        return;
      }
    }
    
    // Fallback to provided path or dashboard
    navigate(fallbackPath);
  };

  // Get the previous entry for displaying contextual information
  const previousEntry = getPreviousEntry();
  const backLabel = previousEntry ? `Back to ${previousEntry.title}` : fallbackLabel;

  return (
    <button
      onClick={handleBack}
      className={className}
      title={backLabel}
    >
      <ArrowLeft className="h-4 w-4 mr-2" />
      {canGoBack && previousEntry ? (
        <span>Back to {previousEntry.title}</span>
      ) : (
        <span>{fallbackLabel}</span>
      )}
    </button>
  );
};

export default BackButton;