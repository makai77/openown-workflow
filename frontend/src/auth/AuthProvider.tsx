import { useEffect, useState } from "react";
import type { ReactNode } from "react";

import { fetchMe, login as apiLogin, logout as apiLogout } from "@/api/auth";
import type { CurrentUser } from "@/api/auth";
import { getToken } from "@/api/client";

import { AuthContext } from "./context";
import type { AuthStatus } from "./context";

// Holds the session: the current user + a status the router uses to gate routes.
// On mount, if a token is already stored, resolve the user from /me; a failure
// (expired/invalid token) clears it and drops to anonymous. The backend remains
// the sole authority on what each role may do — this only decides which screens
// to render.
export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [status, setStatus] = useState<AuthStatus>(() =>
    getToken() ? "loading" : "anonymous",
  );

  useEffect(() => {
    if (!getToken()) return;
    let active = true;
    fetchMe()
      .then((me) => {
        if (!active) return;
        setUser(me);
        setStatus("authenticated");
      })
      .catch(() => {
        if (!active) return;
        apiLogout();
        setUser(null);
        setStatus("anonymous");
      });
    return () => {
      active = false;
    };
  }, []);

  async function login(email: string, password: string): Promise<CurrentUser> {
    const me = await apiLogin(email, password);
    setUser(me);
    setStatus("authenticated");
    return me;
  }

  function logout(): void {
    apiLogout();
    setUser(null);
    setStatus("anonymous");
  }

  return (
    <AuthContext.Provider value={{ user, status, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
