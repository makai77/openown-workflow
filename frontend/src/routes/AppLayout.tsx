import { Link, Outlet, useNavigate } from "react-router-dom";

import { useAuth } from "@/auth/context";

// Shell for authenticated screens: a header with the current user and sign-out,
// plus the routed content.
export function AppLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/login", { replace: true });
  }

  // The brand link points at the signed-in role's home so it never bounces a
  // reviewer through the applicant route guard.
  const home =
    user?.role === "REVIEWER" ? "/reviewer/applications" : "/applications";

  return (
    <div className="min-h-svh">
      <header className="flex items-center justify-between border-b px-4 py-3">
        <Link to={home} className="font-semibold">
          Open Ownership
        </Link>
        <div className="flex items-center gap-3 text-sm">
          {user ? (
            <span className="text-gray-500">{user.name || user.email}</span>
          ) : null}
          <button
            type="button"
            onClick={handleLogout}
            className="rounded border px-2 py-1"
          >
            Sign out
          </button>
        </div>
      </header>
      <main className="mx-auto max-w-3xl p-4">
        <Outlet />
      </main>
    </div>
  );
}
