/**
 * @format
 */

import React from 'react';
import ReactTestRenderer, {ReactTestInstance} from 'react-test-renderer';
import {Button, Text, TextInput} from 'react-native';
import {SafeAreaView} from 'react-native-safe-area-context';
import App from '../App';

/**
 * `.root` throws "Can't access .root on unmounted test renderer" while it is
 * read inside the act() that creates the tree, so mount and query separately.
 */
function mount(): ReactTestInstance {
  let tree: ReactTestRenderer.ReactTestRenderer | undefined;
  ReactTestRenderer.act(() => {
    tree = ReactTestRenderer.create(<App />);
  });
  return tree!.root;
}

/** Every mounted Text node, concatenated, so assertions can key on screen copy. */
function visibleText(root: ReactTestInstance): string {
  return root
    .findAllByType(Text)
    .map(node => {
      const children = Array.isArray(node.props.children)
        ? node.props.children
        : [node.props.children];
      return children
        .filter(c => typeof c === 'string' || typeof c === 'number')
        .join('');
    })
    .join('|');
}

function buttonByTitle(
  root: ReactTestInstance,
  title: string,
): ReactTestInstance | undefined {
  return root.findAll(n => n.type === Button && n.props.title === title)[0];
}

function press(root: ReactTestInstance, title: string): void {
  const button = buttonByTitle(root, title);
  if (!button) {
    throw new Error(`no Button titled ${title} is mounted`);
  }
  ReactTestRenderer.act(() => {
    button.props.onPress();
  });
}

/**
 * Guard against the vacuous-render failure mode: a provider that swallows its
 * children leaves a tree that "renders" but contains nothing, and every
 * findAll-based expectation passes as empty.
 */
function expectRealTree(root: ReactTestInstance): void {
  expect(root.findAllByType(Button).length).toBeGreaterThanOrEqual(2);
  expect(root.findAllByType(Text).length).toBeGreaterThan(0);
}

test('boots on chat: the composer is mounted and the map screen is not', () => {
  const root = mount();
  expectRealTree(root);
  expect(root.findAllByType(TextInput)).toHaveLength(1);
  expect(buttonByTitle(root, '搜身边 1km')).toBeUndefined();
  expect(buttonByTitle(root, '聊天')!.props.disabled).toBe(true);
});

test('身边 swaps in the map screen and drops the chat composer', () => {
  const root = mount();
  expectRealTree(root);
  press(root, '身边');
  expect(buttonByTitle(root, '搜身边 1km')).toBeDefined();
  expect(root.findAllByType(TextInput)).toHaveLength(0);
  expect(visibleText(root)).toContain('地图占位');
  expect(buttonByTitle(root, '身边')!.props.disabled).toBe(true);
});

test('switching back to 聊天 remounts the composer', () => {
  const root = mount();
  press(root, '身边');
  press(root, '聊天');
  expect(root.findAllByType(TextInput)).toHaveLength(1);
  expect(buttonByTitle(root, '搜身边 1km')).toBeUndefined();
});

/**
 * RN 0.87 ships edgeToEdgeEnabled=true, so a plain View root draws its first row
 * under the status bar. On the emulator that made both tabs un-tappable; the web
 * preview has no status bar, so only this assertion catches it in CI.
 */
test('the root container insets the status bar and the navigation bar', () => {
  const root = mount();
  const [container] = root.findAllByType(SafeAreaView);
  expect(container).toBeDefined();
  expect(container.props.edges).toEqual(
    expect.arrayContaining(['top', 'bottom']),
  );
});
