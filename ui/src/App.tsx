import React from 'react'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import AuctionDetails from './pages/AuctionDetails'
import AuctionHouseDetails from './pages/AuctionHouseDetails'
import RoundDetails from './pages/RoundDetails'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30 * 1000, // 30 seconds
      refetchInterval: 30 * 1000, // Refetch every 30 seconds
      retry: 2,
    },
  },
})

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <Layout>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/auction/:address" element={<AuctionDetails />} />
            <Route path="/auction-house/:address" element={<AuctionHouseDetails />} />
            <Route path="/round/:auctionHouse/:roundId" element={<RoundDetails />} />
          </Routes>
        </Layout>
      </Router>
    </QueryClientProvider>
  )
}

export default App