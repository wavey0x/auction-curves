import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { useLocation } from 'react-router-dom';

interface NavigationEntry {
  path: string;
  title: string;
  params?: Record<string, string>;
  scrollY: number;
  timestamp: number;
}

interface NavigationContextType {
  history: NavigationEntry[];
  pushHistory: (entry: Omit<NavigationEntry, 'timestamp'>) => void;
  goBack: () => string | null;
  clearHistory: () => void;
  canGoBack: boolean;
  getPreviousEntry: () => NavigationEntry | null;
}

const NavigationContext = createContext<NavigationContextType | undefined>(undefined);

const STORAGE_KEY = 'auction_navigation_history';
const MAX_HISTORY_SIZE = 10;

// Helper function to generate page titles
const generatePageTitle = (path: string): string => {
  if (path === '/') return 'Dashboard';
  
  const segments = path.split('/').filter(Boolean);
  
  if (segments[0] === 'auction' && segments.length >= 3) {
    const address = segments[2];
    return `Auction ${address.slice(0, 6)}...${address.slice(-4)}`;
  }
  
  if (segments[0] === 'round' && segments.length >= 4) {
    const roundId = segments[3];
    return `Round ${roundId}`;
  }
  
  return 'Page';
};

interface NavigationProviderProps {
  children: ReactNode;
}

export const NavigationProvider: React.FC<NavigationProviderProps> = ({ children }) => {
  const location = useLocation();
  const [history, setHistory] = useState<NavigationEntry[]>([]);

  // Load history from localStorage on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const parsedHistory = JSON.parse(stored);
        setHistory(parsedHistory);
      }
    } catch (error) {
      console.warn('Failed to load navigation history from localStorage:', error);
    }
  }, []);

  // Save history to localStorage whenever it changes
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(history));
    } catch (error) {
      console.warn('Failed to save navigation history to localStorage:', error);
    }
  }, [history]);

  // Track route changes and automatically push to history
  useEffect(() => {
    const currentEntry: NavigationEntry = {
      path: location.pathname,
      title: generatePageTitle(location.pathname),
      scrollY: 0,
      timestamp: Date.now(),
    };

    // Don't add duplicate entries for the same path
    setHistory(prev => {
      const lastEntry = prev[prev.length - 1];
      if (lastEntry && lastEntry.path === currentEntry.path) {
        return prev;
      }
      
      const newHistory = [...prev, currentEntry];
      // Keep only the last MAX_HISTORY_SIZE entries
      return newHistory.slice(-MAX_HISTORY_SIZE);
    });
  }, [location.pathname]);

  const pushHistory = (entry: Omit<NavigationEntry, 'timestamp'>) => {
    const newEntry: NavigationEntry = {
      ...entry,
      timestamp: Date.now(),
    };

    setHistory(prev => {
      // Don't add duplicate entries for the same path
      const lastEntry = prev[prev.length - 1];
      if (lastEntry && lastEntry.path === newEntry.path) {
        return prev;
      }
      
      const newHistory = [...prev, newEntry];
      return newHistory.slice(-MAX_HISTORY_SIZE);
    });
  };

  const goBack = (): string | null => {
    // Get the previous entry (second to last, since last is current page)
    if (history.length < 2) {
      return '/'; // Default to dashboard
    }

    const previousEntry = history[history.length - 2];
    
    // Remove current entry from history when going back
    setHistory(prev => prev.slice(0, -1));
    
    return previousEntry.path;
  };

  const clearHistory = () => {
    setHistory([]);
  };

  const canGoBack = history.length > 1;

  const getPreviousEntry = (): NavigationEntry | null => {
    if (history.length < 2) return null;
    return history[history.length - 2];
  };

  const value: NavigationContextType = {
    history,
    pushHistory,
    goBack,
    clearHistory,
    canGoBack,
    getPreviousEntry,
  };

  return (
    <NavigationContext.Provider value={value}>
      {children}
    </NavigationContext.Provider>
  );
};

export const useNavigation = (): NavigationContextType => {
  const context = useContext(NavigationContext);
  if (!context) {
    throw new Error('useNavigation must be used within a NavigationProvider');
  }
  return context;
};