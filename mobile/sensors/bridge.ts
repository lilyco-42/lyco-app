/** NativeBridge: the only seam between sensors logic and React Native.
 * The RN adapter (later) implements this with PermissionsAndroid /
 * react-native-permissions. Tests inject fakes. No RN imports here. */

export type PermissionStatus = "granted" | "denied" | "never_ask_again";

export type PermissionName =
  | "location-fine"
  | "location-coarse"
  | "location-background"
  | "camera"
  | "microphone"
  | "notifications"
  | "contacts"
  | "calendar"
  | "photos";

export interface NativeBridge {
  checkPermission(name: PermissionName): Promise<PermissionStatus>;
  requestPermission(name: PermissionName): Promise<PermissionStatus>;
}
