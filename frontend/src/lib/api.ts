export const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export type ApiError = Error & { status?: number };

export function getToken() {
  if (typeof window === "undefined") return "";
  return localStorage.getItem("agri_token") || "";
}

export function setAuth(token: string, user: unknown) {
  localStorage.setItem("agri_token", token);
  localStorage.setItem("agri_user", JSON.stringify(user));
}

export function clearAuth() {
  localStorage.removeItem("agri_token");
  localStorage.removeItem("agri_user");
}

export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers = new Headers(init.headers);
  if (!(init.body instanceof FormData)) headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(`${API_BASE}${path}`, { ...init, headers });
  if (response.status === 401 && typeof window !== "undefined") {
    window.location.href = "/login";
  }
  if (!response.ok) {
    const message = await response.text();
    const error: ApiError = new Error(message || "请求失败");
    error.status = response.status;
    throw error;
  }
  return response.json() as Promise<T>;
}
