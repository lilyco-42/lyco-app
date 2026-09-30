import React from 'react';
import {View} from 'react-native';

/**
 * Preview-lane shim: react-native-safe-area-context resolves to its native
 * entry under react-native-web, and its provider then renders a component
 * object that React rejects ("Element type is invalid ... got: object",
 * thrown inside its `hookified` dependency). A browser has no notch, so zero
 * insets are also the semantically correct answer here.
 *
 * Scope: only .storybook/main.ts aliases to this file. The RN app and the jest
 * lane keep using the real package.
 */
export const __lycoShim = true;

const frame = {x: 0, y: 0, width: 390, height: 844};
const insets = {top: 0, right: 0, bottom: 0, left: 0};

export const SafeAreaProvider = ({children}: {children?: React.ReactNode}) =>
  <>{children}</>;

export const SafeAreaView = ({children, style}: any) => (
  <View style={style}>{children}</View>
);

export const useSafeAreaInsets = () => insets;
export const useSafeAreaFrame = () => frame;
export const initialWindowMetrics = {frame, insets};

export default {
  SafeAreaProvider,
  SafeAreaView,
  useSafeAreaInsets,
  useSafeAreaFrame,
  initialWindowMetrics,
};
