import React from 'react';
import {ChatScreen} from '../screens/ChatScreen';
import {MapScreen} from '../screens/MapScreen';

export default {
  title: 'Screens',
};

/** ASCII story names keep the generated ids stable for scripts and CI. */
export const Chat = () => <ChatScreen />;

export const Nearby = () => <MapScreen />;
