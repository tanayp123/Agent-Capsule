"use client";

const STORAGE_KEY = "agent-capsule-console-session-token";

export function getEphemeralSessionToken() {
  if (typeof window === "undefined") {
    return "server-render-placeholder";
  }

  const existing = window.sessionStorage.getItem(STORAGE_KEY);
  if (existing) {
    return existing;
  }

  const bytes = new Uint8Array(24);
  window.crypto.getRandomValues(bytes);
  const token = Array.from(bytes)
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
  window.sessionStorage.setItem(STORAGE_KEY, token);
  return token;
}

export function rotateEphemeralSessionToken() {
  if (typeof window === "undefined") {
    return "server-render-placeholder";
  }

  window.sessionStorage.removeItem(STORAGE_KEY);
  return getEphemeralSessionToken();
}

export function setEphemeralSessionToken(token: string) {
  if (typeof window === "undefined") {
    return "server-render-placeholder";
  }

  window.sessionStorage.setItem(STORAGE_KEY, token);
  return token;
}
