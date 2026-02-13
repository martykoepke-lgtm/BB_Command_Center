import { api } from "./client";
import type { AuthResponse, LoginRequest, RegisterRequest, UserOut } from "@/types/api";

export const authApi = {
  login: (data: LoginRequest) =>
    api.post<AuthResponse>("/api/auth/login", data),

  register: (data: RegisterRequest) =>
    api.post<AuthResponse>("/api/auth/register", data),

  me: () =>
    api.get<UserOut>("/api/auth/me"),
};
