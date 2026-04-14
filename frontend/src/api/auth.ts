import { api } from "./client";

export interface UserResponse {
  id: number;
  username: string;
  role: string;
  daily_quota: number;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export async function login(
  username: string,
  password: string,
): Promise<TokenResponse> {
  // FastAPI expects OAuth2 form-encoded, not JSON
  const form = new URLSearchParams();
  form.set("username", username);
  form.set("password", password);

  return api
    .post("auth/login", { body: form })
    .json<TokenResponse>();
}

export async function register(
  username: string,
  password: string,
): Promise<UserResponse> {
  return api
    .post("auth/register", { json: { username, password } })
    .json<UserResponse>();
}

export async function getMe(): Promise<UserResponse> {
  return api.get("auth/me").json<UserResponse>();
}
