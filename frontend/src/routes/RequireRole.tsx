import { Navigate, Outlet } from "react-router-dom";

import type { Role } from "@/api/auth";
import { useAuth } from "@/auth/context";

// Keeps each role on its own screens. This is a UX convenience, not a security
// boundary — the backend rejects any cross-role API call regardless of routing.
// The prop is named `allow` (not `role`) so it isn't mistaken for an ARIA role.
export function RequireRole({ allow }: { allow: Role }) {
  const { user } = useAuth();

  if (user && user.role !== allow) {
    return (
      <Navigate
        to={user.role === "REVIEWER" ? "/reviewer/applications" : "/applications"}
        replace
      />
    );
  }
  return <Outlet />;
}
