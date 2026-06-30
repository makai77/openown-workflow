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
  const roleLabel = user?.role === "REVIEWER" ? "Reviewer" : "Applicant";

  return (
    <div className="min-h-svh">
      <header className="sticky top-0 z-10 border-b bg-white/90 backdrop-blur">
        <div className="mx-auto flex max-w-3xl items-center justify-between px-4 py-3">
          <Link to={home} className="flex items-center gap-2 font-semibold">
            <span
              className="grid size-6 place-items-center rounded bg-brand text-xs font-bold text-white"
              aria-hidden="true"
            >
              OO
            </span>
            Open Ownership
          </Link>
          <div className="flex items-center gap-3 text-sm">
            {user ? (
              <span className="flex items-center gap-2 text-gray-500">
                <span className="hidden sm:inline">
                  {user.name || user.email}
                </span>
                <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600">
                  {roleLabel}
                </span>
              </span>
            ) : null}
            <button
              type="button"
              onClick={handleLogout}
              className="rounded border px-2 py-1 hover:bg-gray-50"
            >
              Sign out
            </button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-3xl p-4">
        <Outlet />
      </main>
    </div>
  );
}
