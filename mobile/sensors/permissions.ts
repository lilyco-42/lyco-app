/** Permission flow logic: check first, request only when needed.
 * never_ask_again short-circuits (must guide user to settings instead).
 */
import type { NativeBridge, PermissionName, PermissionStatus } from "./bridge.ts";

export type PermissionResult = {
  name: PermissionName;
  status: PermissionStatus;
  requested: boolean;
};

export async function ensurePermission(
  bridge: NativeBridge,
  name: PermissionName
): Promise<PermissionResult> {
  const current = await bridge.checkPermission(name);
  if (current === "granted" || current === "never_ask_again") {
    return { name, status: current, requested: false };
  }
  const after = await bridge.requestPermission(name);
  return { name, status: after, requested: true };
}

export async function ensureAll(
  bridge: NativeBridge,
  names: PermissionName[]
): Promise<PermissionResult[]> {
  const out: PermissionResult[] = [];
  for (const name of names) {
    out.push(await ensurePermission(bridge, name));
  }
  return out;
}
