import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { getSystemTags, getSystemTag } from '../data/systemTags';

// Types
interface UserTags {
  [address: string]: string; // lowercase address -> tag name
}

interface AddressTagsContextValue {
  // Get tag for address (checks user first, then system)
  getTag: (address: string) => string | null;
  getDisplayName: (address: string) => string;
  
  // User tag management
  getUserTags: () => UserTags;
  setUserTag: (address: string, tag: string) => void;
  removeUserTag: (address: string) => void;
  clearUserTags: () => void;
  hasUserTag: (address: string) => boolean;
  
  // System tags (read-only)
  getSystemTags: () => Record<string, string>;
  hasSystemTag: (address: string) => boolean;
  
  // System tag enable/disable
  isSystemTagDisabled: (address: string) => boolean;
  disableSystemTag: (address: string) => void;
  enableSystemTag: (address: string) => void;
  toggleSystemTag: (address: string) => void;
  
  // Statistics
  getUserTagCount: () => number;
  getSystemTagCount: () => number;
  
  // Import/Export
  exportUserTags: () => string;
  importUserTags: (jsonString: string) => { success: boolean; error?: string };
}

const AddressTagsContext = createContext<AddressTagsContextValue | undefined>(undefined);

const STORAGE_KEY = 'addressTags';
const DISABLED_SYSTEM_TAGS_KEY = 'disabledSystemTags';

// Helper to normalize addresses for consistent storage/lookup
function normalizeAddress(address: string): string {
  return address.toLowerCase();
}

export const AddressTagsProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  // Load user tags from localStorage on initialization
  const [userTags, setUserTags] = useState<UserTags>(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw);
        // Ensure all keys are lowercase for consistency
        const normalized: UserTags = {};
        Object.entries(parsed).forEach(([addr, tag]) => {
          if (typeof tag === 'string' && tag.trim()) {
            normalized[normalizeAddress(addr)] = tag.trim();
          }
        });
        return normalized;
      }
    } catch (error) {
      console.warn('Failed to load user address tags from localStorage:', error);
    }
    return {};
  });

  // Load disabled system tags from localStorage
  const [disabledSystemTags, setDisabledSystemTags] = useState<Set<string>>(() => {
    try {
      const raw = localStorage.getItem(DISABLED_SYSTEM_TAGS_KEY);
      if (raw) {
        const parsed = JSON.parse(raw);
        if (Array.isArray(parsed)) {
          return new Set(parsed.map(addr => normalizeAddress(addr)));
        }
      }
    } catch (error) {
      console.warn('Failed to load disabled system tags from localStorage:', error);
    }
    return new Set();
  });

  // Persist user tags to localStorage whenever they change
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(userTags));
    } catch (error) {
      console.warn('Failed to save user address tags to localStorage:', error);
    }
  }, [userTags]);

  // Persist disabled system tags to localStorage whenever they change
  useEffect(() => {
    try {
      localStorage.setItem(DISABLED_SYSTEM_TAGS_KEY, JSON.stringify([...disabledSystemTags]));
    } catch (error) {
      console.warn('Failed to save disabled system tags to localStorage:', error);
    }
  }, [disabledSystemTags]);

  // Main API functions
  const getTag = (address: string): string | null => {
    const normalized = normalizeAddress(address);
    
    // Check user tags first (higher precedence)
    if (normalized in userTags) {
      return userTags[normalized];
    }
    
    // Fallback to system tags if not disabled
    if (disabledSystemTags.has(normalized)) {
      return null;
    }
    
    return getSystemTag(normalized);
  };

  const getDisplayName = (address: string): string => {
    const tag = getTag(address);
    return tag || address;
  };

  const getUserTags = (): UserTags => {
    return { ...userTags };
  };

  const setUserTag = (address: string, tag: string): void => {
    const normalized = normalizeAddress(address);
    const trimmedTag = tag.trim();
    
    if (!trimmedTag) {
      removeUserTag(address);
      return;
    }
    
    setUserTags(prev => ({
      ...prev,
      [normalized]: trimmedTag
    }));
  };

  const removeUserTag = (address: string): void => {
    const normalized = normalizeAddress(address);
    setUserTags(prev => {
      const next = { ...prev };
      delete next[normalized];
      return next;
    });
  };

  const clearUserTags = (): void => {
    setUserTags({});
  };

  const hasUserTag = (address: string): boolean => {
    const normalized = normalizeAddress(address);
    return normalized in userTags;
  };

  const hasSystemTag = (address: string): boolean => {
    const normalized = normalizeAddress(address);
    return getSystemTag(normalized) !== null;
  };

  const getUserTagCount = (): number => {
    return Object.keys(userTags).length;
  };

  const getSystemTagCount = (): number => {
    return Object.keys(getSystemTags()).length;
  };

  const isSystemTagDisabled = (address: string): boolean => {
    const normalized = normalizeAddress(address);
    return disabledSystemTags.has(normalized);
  };

  const disableSystemTag = (address: string): void => {
    const normalized = normalizeAddress(address);
    setDisabledSystemTags(prev => new Set([...prev, normalized]));
  };

  const enableSystemTag = (address: string): void => {
    const normalized = normalizeAddress(address);
    setDisabledSystemTags(prev => {
      const next = new Set(prev);
      next.delete(normalized);
      return next;
    });
  };

  const toggleSystemTag = (address: string): void => {
    if (isSystemTagDisabled(address)) {
      enableSystemTag(address);
    } else {
      disableSystemTag(address);
    }
  };

  const exportUserTags = (): string => {
    return JSON.stringify(userTags, null, 2);
  };

  const importUserTags = (jsonString: string): { success: boolean; error?: string } => {
    try {
      const parsed = JSON.parse(jsonString);
      
      if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
        return { success: false, error: 'Invalid format: must be an object' };
      }
      
      // Validate and normalize the imported data
      const normalized: UserTags = {};
      let validCount = 0;
      
      Object.entries(parsed).forEach(([addr, tag]) => {
        if (typeof tag === 'string' && tag.trim() && 
            typeof addr === 'string' && addr.match(/^0x[a-fA-F0-9]{40}$/)) {
          normalized[normalizeAddress(addr)] = tag.trim();
          validCount++;
        }
      });
      
      if (validCount === 0) {
        return { success: false, error: 'No valid address-tag pairs found' };
      }
      
      // Merge with existing tags (imported tags take precedence)
      setUserTags(prev => ({ ...prev, ...normalized }));
      
      return { success: true };
    } catch (error) {
      return { success: false, error: 'Invalid JSON format' };
    }
  };

  // Memoize the context value to prevent unnecessary re-renders
  const value = useMemo(() => ({
    getTag,
    getDisplayName,
    getUserTags,
    setUserTag,
    removeUserTag,
    clearUserTags,
    hasUserTag,
    getSystemTags,
    hasSystemTag,
    isSystemTagDisabled,
    disableSystemTag,
    enableSystemTag,
    toggleSystemTag,
    getUserTagCount,
    getSystemTagCount,
    exportUserTags,
    importUserTags,
  }), [userTags, disabledSystemTags]); // Recreate when userTags or disabledSystemTags change

  return (
    <AddressTagsContext.Provider value={value}>
      {children}
    </AddressTagsContext.Provider>
  );
};

// Hook for consuming the context
export const useAddressTags = () => {
  const context = useContext(AddressTagsContext);
  if (!context) {
    throw new Error('useAddressTags must be used within AddressTagsProvider');
  }
  return context;
};

export default AddressTagsContext;