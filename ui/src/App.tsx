import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import AuctionDetails from "./pages/AuctionDetails";
import RoundDetails from "./pages/RoundDetails";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 0, // Consider data stale immediately for development
      refetchInterval: 5 * 1000, // Refetch every 5 seconds
      retry: 2,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <Layout>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/auction/:chainId/:address" element={<AuctionDetails />} />
            <Route
              path="/round/:chainId/:auctionAddress/:roundId"
              element={<RoundDetails />}
            />
          </Routes>
        </Layout>
      </Router>
    </QueryClientProvider>
  );
}

export default App;
