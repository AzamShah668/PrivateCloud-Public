import { useQuery } from "@tanstack/react-query";
import { getMe } from "@/api/auth";
import { useAuthStore } from "@/stores/auth-store";
import { useEffect } from "react";

export function useCurrentUser() {
  const { token, setUser, logout } = useAuthStore();

  const query = useQuery({
    queryKey: ["user", "me"],
    queryFn: getMe,
    enabled: !!token,
    retry: false,
  });

  useEffect(() => {
    if (query.data) setUser(query.data);
    if (query.error) logout();
  }, [query.data, query.error, setUser, logout]);

  return query;
}
