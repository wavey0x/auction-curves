import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import AuctionDetails from "./pages/AuctionDetails";
import RoundDetails from "./pages/RoundDetails";
import ApiDocs from "./pages/ApiDocs";
import { NavigationProvider } from "./contexts/NavigationProvider";

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

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <UserSettingsProvider>
        <Router>
          <NavigationProvider>
            <Layout>
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/auction/:chainId/:address" element={<AuctionDetails />} />
                <Route
                  path="/round/:chainId/:auctionAddress/:roundId"
                  element={<RoundDetails />}
                />
                <Route path="/api-docs" element={<ApiDocs />} />
              </Routes>
            </Layout>
          </NavigationProvider>
        </Router>
      </UserSettingsProvider>
    </QueryClientProvider>
  );
}
import { UserSettingsProvider } from "./context/UserSettingsContext";

export default App;
