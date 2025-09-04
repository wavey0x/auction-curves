import { BrowserRouter as Router, Routes, Route, useLocation, useNavigate } from "react-router-dom";
import React, { useEffect } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import AuctionDetails from "./pages/AuctionDetails";
import RoundDetails from "./pages/RoundDetails";
import TakerDetails from "./pages/TakerDetails";
import TakeDetails from "./pages/TakeDetails";
import ApiDocs from "./pages/ApiDocs";
import StatusPage from "./pages/Status";
import { NavigationProvider } from "./contexts/NavigationProvider";
import { UserSettingsProvider } from "./context/UserSettingsContext";
import { AddressTagsProvider } from "./context/AddressTagsContext";
import { NotificationProvider } from "./context/NotificationContext";

// Global refresh interval - change this to adjust all auto-refresh timing
const REFRESH_INTERVAL = 5 * 60 * 1000; // 5 minutes

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 0, // Consider data stale immediately for development
      refetchInterval: REFRESH_INTERVAL, // Global auto-refresh interval
      retry: 2,
    },
  },
});

// Ensures that hitting "/" without a hash redirects to the last active dashboard tab
function HomeTabHashInitializer() {
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    // Only when on home path without an explicit hash
    if (location.pathname === "/" && (!location.hash || location.hash === "")) {
      try {
        const stored = localStorage.getItem('dashboard_active_tab');
        const valid = stored && ['active-rounds','takes','takers','all-auctions'].includes(stored);
        if (valid) {
          navigate({ pathname: location.pathname, search: location.search, hash: stored as string }, { replace: true });
        }
      } catch (e) {
        // ignore
      }
    }
    // run once on mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return null;
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <UserSettingsProvider>
        <AddressTagsProvider>
          <NotificationProvider>
            <Router>
          <HomeTabHashInitializer />
          <NavigationProvider>
            <Layout>
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/status" element={<StatusPage />} />
                <Route path="/auction/:chainId/:address" element={<AuctionDetails />} />
                <Route
                  path="/round/:chainId/:auctionAddress/:roundId"
                  element={<RoundDetails />}
                />
                <Route path="/taker/:address" element={<TakerDetails />} />
                <Route path="/take/:chainId/:auctionAddress/:roundId/:takeSeq" element={<TakeDetails />} />
                <Route path="/api-docs" element={<ApiDocs />} />
              </Routes>
            </Layout>
          </NavigationProvider>
            </Router>
          </NotificationProvider>
        </AddressTagsProvider>
      </UserSettingsProvider>
    </QueryClientProvider>
  );
}

export default App;
