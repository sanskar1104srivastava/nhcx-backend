// src/hooks/usePermissions.ts
// Stub until real role/auth logic exists in NHCX-Frontend-1 —
// treats everyone as admin for now so the Approve/Reject actions show up.
// Replace with real role-checking logic once login/auth is added.
export function usePermissions() {
  return { isAdmin: true };
}
