/**
 * react-native-safe-area-context's provider reads the RNSSafeAreaContext native
 * module, which does not exist under react-test-renderer. Unmocked it renders
 * *no children at all*, so every `App.test.tsx` assertion silently runs against
 * an empty tree. This passthrough is picked up automatically because the real
 * package is in node_modules.
 */
const frame = {x: 0, y: 0, width: 375, height: 812};
const insets = {top: 0, right: 0, bottom: 0, left: 0};

module.exports = {
  SafeAreaProvider: ({children}) => children,
  SafeAreaView: ({children}) => children,
  useSafeAreaInsets: () => insets,
  useSafeAreaFrame: () => frame,
  initialWindowMetrics: {frame, insets},
};
