import React from 'react';

/** Frame the story in a phone-sized viewport so proportions are readable. */
export const parameters = {
  layout: 'centered',
};

export const decorators = [
  (Story: () => React.ReactElement) => (
    <div
      style={{
        width: 390,
        height: 844,
        background: '#fff',
        border: '1px solid #d6d8dc',
        borderRadius: 30,
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      <Story />
    </div>
  ),
];
