import { BrowserRouter, Routes, Route } from "react-router-dom"
import { AppLayout } from "@/components/layout/AppLayout"
import { ErrorBoundary } from "@/components/shared/ErrorBoundary"
import DashboardPage from "@/pages/DashboardPage"
import ProfilePage from "@/pages/ProfilePage"
import RunsListPage from "@/pages/RunsListPage"
import RunDetailPage from "@/pages/RunDetailPage"
import ResultsPage from "@/pages/OpportunitiesPage"
import CoverLettersPage from "@/pages/CoverLettersPage"
import PoliciesPage from "@/pages/PoliciesPage"
import NotFoundPage from "@/pages/NotFoundPage"

export default function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <Routes>
          <Route element={<AppLayout />}>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/profiles/:profileId" element={<ProfilePage />} />
            <Route path="/profiles/:profileId/runs" element={<RunsListPage />} />
            <Route path="/profiles/:profileId/runs/:runId" element={<RunDetailPage />} />
            <Route path="/profiles/:profileId/results" element={<ResultsPage />} />
            <Route path="/profiles/:profileId/cover-letters" element={<CoverLettersPage />} />
            <Route path="/policies" element={<PoliciesPage />} />
            <Route path="*" element={<NotFoundPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ErrorBoundary>
  )
}
