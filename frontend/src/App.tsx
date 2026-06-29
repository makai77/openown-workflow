import { Navigate, Route, Routes } from "react-router-dom";

import { LoginPage } from "@/auth/LoginPage";
import { ApplicationDetailPage } from "@/applications/ApplicationDetailPage";
import {
  EditApplicationPage,
  NewApplicationPage,
} from "@/applications/ApplicationForm";
import { MyApplicationsPage } from "@/applications/MyApplicationsPage";
import { ReviewerApplicationDetailPage } from "@/reviewer/ReviewerApplicationDetailPage";
import { ReviewerQueuePage } from "@/reviewer/ReviewerQueuePage";
import { AppLayout } from "@/routes/AppLayout";
import { RequireAuth } from "@/routes/RequireAuth";
import { RequireRole } from "@/routes/RequireRole";

function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<RequireAuth />}>
        <Route element={<RequireRole allow="APPLICANT" />}>
          <Route element={<AppLayout />}>
            <Route path="/applications" element={<MyApplicationsPage />} />
            <Route path="/applications/new" element={<NewApplicationPage />} />
            <Route path="/applications/:id" element={<ApplicationDetailPage />} />
            <Route
              path="/applications/:id/edit"
              element={<EditApplicationPage />}
            />
          </Route>
        </Route>
        <Route element={<RequireRole allow="REVIEWER" />}>
          <Route element={<AppLayout />}>
            <Route
              path="/reviewer/applications"
              element={<ReviewerQueuePage />}
            />
            <Route
              path="/reviewer/applications/:id"
              element={<ReviewerApplicationDetailPage />}
            />
          </Route>
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/applications" replace />} />
    </Routes>
  );
}

export default App;
