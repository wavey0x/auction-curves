import React, { createContext, useContext, useEffect, useMemo, useState } from "react";
import { rpcService } from "../lib/rpcService";

type ValueDisplay = 'usd' | 'token';

interface UserSettings {
  defaultValueDisplay: ValueDisplay;
  setDefaultValueDisplay: (v: ValueDisplay) => void;
  // Custom RPC settings
  customRpcEnabled: boolean;
  setCustomRpcEnabled: (v: boolean) => void;
  customRpcUrl: string;
  setCustomRpcUrl: (v: string) => void;
  // Warning flow when custom RPC fails
  customRpcWarning: { visible: boolean; message?: string };
  dismissCustomRpcWarning: () => void;
  disableCustomRpc: () => void;
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

  // Custom RPC state
  const [customRpcEnabled, setCustomRpcEnabled] = useState<boolean>(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw);
        return !!parsed.customRpcEnabled;
      }
    } catch {}
    return false;
  });

  const [customRpcUrl, setCustomRpcUrl] = useState<string>(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw);
        if (typeof parsed.customRpcUrl === 'string') return parsed.customRpcUrl;
      }
    } catch {}
    return '';
  });

  const [customRpcWarning, setCustomRpcWarning] = useState<{ visible: boolean; message?: string }>({ visible: false });

  // Persist on change
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ 
        defaultValueDisplay,
        customRpcEnabled,
        customRpcUrl
      }));
    } catch {}
  }, [defaultValueDisplay, customRpcEnabled, customRpcUrl]);

  // Wire settings to rpcService
  useEffect(() => {
    rpcService.setCustomRPCConfig(customRpcEnabled, customRpcUrl)
  }, [customRpcEnabled, customRpcUrl])

  // Subscribe to custom RPC error reporting
  useEffect(() => {
    const handler = (error: unknown) => {
      setCustomRpcWarning({
        visible: true,
        message: error instanceof Error ? error.message : 'Custom RPC appears to be failing.'
      })
    }
    rpcService.setCustomRPCErrorHandler(handler)
    return () => { rpcService.setCustomRPCErrorHandler(null) }
  }, [])

  const dismissCustomRpcWarning = () => setCustomRpcWarning({ visible: false })

  const disableCustomRpc = () => {
    setCustomRpcEnabled(false)
    setCustomRpcWarning({ visible: false })
  }

  const value = useMemo(() => ({ 
    defaultValueDisplay, 
    setDefaultValueDisplay,
    customRpcEnabled,
    setCustomRpcEnabled,
    customRpcUrl,
    setCustomRpcUrl,
    customRpcWarning,
    dismissCustomRpcWarning,
    disableCustomRpc
  }), [defaultValueDisplay, customRpcEnabled, customRpcUrl, customRpcWarning]);

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
