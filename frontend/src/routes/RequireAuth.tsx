import { Navigate, Outlet, useLocation } from "react-router-dom";

import { LoadingState } from "@/components/LoadingState";
import { useAuth } from "@/auth/context";

// Gate for any authenticated area. While the session is resolving from a stored
// token we show a loading state; once resolved, anonymous users go to /login.
export function RequireAuth() {
  const { status } = useAuth();
  const location = useLocation();

  if (status === "loading") return <LoadingState />;
  if (status === "anonymous") {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }
  return <Outlet />;
}
