import ky from "ky";
import { useAuthStore } from "@/stores/auth-store";
import { API_BASE } from "@/lib/constants";

export const api = ky.create({
  prefixUrl: API_BASE,
  timeout: 60_000,
  hooks: {
    beforeRequest: [
      (request) => {
        const token = useAuthStore.getState().token;
        if (token) {
          request.headers.set("Authorization", `Bearer ${token}`);
        }
      },
    ],
    afterResponse: [
      (_request, _options, response) => {
        if (response.status === 401) {
          useAuthStore.getState().logout();
        }
      },
    ],
  },
});
