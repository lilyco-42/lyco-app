/**
 * Sample React Native App
 * https://github.com/facebook/react-native
 *
 * @format
 */

import {useState} from 'react';
import {Button, StatusBar, StyleSheet, useColorScheme, View} from 'react-native';
import {SafeAreaProvider, SafeAreaView} from 'react-native-safe-area-context';
import {ChatScreen} from './src/screens/ChatScreen';
import {MapScreen} from './src/screens/MapScreen';

type Tab = 'chat' | 'map';

function App() {
  const isDarkMode = useColorScheme() === 'dark';
  const [tab, setTab] = useState<Tab>('chat');

  return (
    <SafeAreaProvider>
      <StatusBar barStyle={isDarkMode ? 'light-content' : 'dark-content'} />
      <SafeAreaView style={styles.container} edges={['top', 'bottom']}>
        <View style={styles.tabs}>
          <Button
            title="聊天"
            onPress={() => setTab('chat')}
            disabled={tab === 'chat'}
          />
          <Button
            title="身边"
            onPress={() => setTab('map')}
            disabled={tab === 'map'}
          />
        </View>
        {tab === 'chat' ? <ChatScreen /> : <MapScreen />}
      </SafeAreaView>
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  tabs: {
    flexDirection: 'row',
    gap: 8,
    padding: 8,
  },
});

export default App;
