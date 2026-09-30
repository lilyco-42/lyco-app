import {fileURLToPath} from 'node:url';
import type {StorybookConfig} from '@storybook/react-native-web-vite';

const SHIM = fileURLToPath(new URL('./safe-area-web-shim.tsx', import.meta.url));

/**
 * Design-time preview only: this lane renders the real RN components through
 * react-native-web, so layout comes from the same Yoga engine as the device.
 * It is not a substitute for a device run (fonts, native controls, safe areas).
 */
const config: StorybookConfig = {
  stories: ['../App.stories.tsx', '../src/**/*.stories.tsx'],
  framework: {
    name: '@storybook/react-native-web-vite',
    options: {
      // shipped un-transpiled for the web
      modulesToTranspile: ['react-native-safe-area-context'],
    },
  },
  viteFinal: cfg => {
    cfg.plugins = [
      ...(cfg.plugins ?? []),
      {
        // enforce:'pre' so this wins over the react-native-web alias that the
        // framework's vite plugin installs later in the chain.
        name: 'lyco-safe-area-web-shim',
        enforce: 'pre' as const,
        resolveId(id: string) {
          return id === 'react-native-safe-area-context' ? SHIM : null;
        },
      },
    ];
    return cfg;
  },
};

export default config;
