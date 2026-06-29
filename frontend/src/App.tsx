import { Navigate, Route, Routes } from "react-router-dom";

import { LoginPage } from "@/auth/LoginPage";
import { ApplicationDetailPage } from "@/applications/ApplicationDetailPage";
import {
  EditApplicationPage,
  NewApplicationPage,
} from "@/applications/ApplicationForm";
import { MyApplicationsPage } from "@/applications/MyApplicationsPage";
import { AppLayout } from "@/routes/AppLayout";
import { RequireAuth } from "@/routes/RequireAuth";
import { RequireRole } from "@/routes/RequireRole";

// Reviewer screens land in Slice B; until then a reviewer who logs in sees a
// placeholder (and can still sign out) rather than an applicant screen.
function ReviewerPlaceholder() {
  return (
    <p className="text-sm text-gray-500">
      The reviewer queue is coming soon.
    </p>
  );
}

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
        <Route element={<AppLayout />}>
          <Route path="/reviewer" element={<ReviewerPlaceholder />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/applications" replace />} />
    </Routes>
  );
}

export default App;
