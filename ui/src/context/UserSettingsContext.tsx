import React, { createContext, useContext, useEffect, useMemo, useState } from "react";

type ValueDisplay = 'usd' | 'token';

interface UserSettings {
  defaultValueDisplay: ValueDisplay;
  setDefaultValueDisplay: (v: ValueDisplay) => void;
}

const UserSettingsContext = createContext<UserSettings | undefined>(undefined);

const STORAGE_KEY = 'userSettings';

export const UserSettingsProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [defaultValueDisplay, setDefaultValueDisplay] = useState<ValueDisplay>(() => {
    // Initialize from localStorage immediately
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw);
        if (parsed.defaultValueDisplay === 'usd' || parsed.defaultValueDisplay === 'token') {
          return parsed.defaultValueDisplay;
        }
      }
    } catch {}
    return 'token'; // fallback
  });

  // No need for loading effect anymore since we initialize directly

  // Persist on change
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ defaultValueDisplay }));
    } catch {}
  }, [defaultValueDisplay]);

  const value = useMemo(() => ({ defaultValueDisplay, setDefaultValueDisplay }), [defaultValueDisplay]);

  return (
    <UserSettingsContext.Provider value={value}>
      {children}
    </UserSettingsContext.Provider>
  );
};

export const useUserSettings = () => {
  const ctx = useContext(UserSettingsContext);
  if (!ctx) throw new Error('useUserSettings must be used within UserSettingsProvider');
  return ctx;
};

