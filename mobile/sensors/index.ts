/** sensors module public surface. */
import type { PermissionName } from "./bridge.ts";

export type { NativeBridge, PermissionName, PermissionStatus } from "./bridge.ts";
export { ensurePermission, ensureAll } from "./permissions.ts";
export type { PermissionResult } from "./permissions.ts";

/** Full catalog; mirrors docs/PERMISSIONS.md (side-load priority order). */
export const PERMISSIONS: PermissionName[] = [
  "location-fine",
  "location-coarse",
  "location-background",
  "camera",
  "microphone",
  "notifications",
  "contacts",
  "calendar",
  "photos",
];
