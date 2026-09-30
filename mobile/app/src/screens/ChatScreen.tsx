import React, {useState} from 'react';
import {
  Button,
  FlatList,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import {createCoreClient} from '../api/core';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  text: string;
}

const client = createCoreClient();

export function ChatScreen() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);

  async function send() {
    const text = input.trim();
    if (!text || busy) {
      return;
    }
    const userMsg: Message = {
      id: `u-${Date.now()}`,
      role: 'user',
      text,
    };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setBusy(true);
    try {
      const res = await client.answer(text);
      setMessages(prev => [
        ...prev,
        {id: `a-${Date.now()}`, role: 'assistant', text: res.response},
      ]);
    } catch (e) {
      setMessages(prev => [
        ...prev,
        {
          id: `e-${Date.now()}`,
          role: 'assistant',
          text: `出错了：${String(e)}`,
        },
      ]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <View style={styles.container}>
      <FlatList
        data={messages}
        keyExtractor={m => m.id}
        style={styles.list}
        renderItem={({item}) => (
          <View
            style={[
              styles.bubble,
              item.role === 'user' ? styles.user : styles.assistant,
            ]}>
            <Text>{item.text}</Text>
          </View>
        )}
      />
      <View style={styles.row}>
        <TextInput
          style={styles.input}
          value={input}
          onChangeText={setInput}
          placeholder="问 Lyco 点什么…"
          editable={!busy}
          onSubmitEditing={send}
        />
        <Button title={busy ? '…' : '发'} onPress={send} disabled={busy} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {flex: 1, padding: 12},
  list: {flex: 1},
  bubble: {padding: 10, marginVertical: 4, borderRadius: 8, maxWidth: '85%'},
  user: {alignSelf: 'flex-end', backgroundColor: '#dbeafe'},
  assistant: {alignSelf: 'flex-start', backgroundColor: '#f3f4f6'},
  row: {flexDirection: 'row', alignItems: 'center', gap: 8, paddingTop: 8},
  input: {
    flex: 1,
    borderWidth: 1,
    borderColor: '#d1d5db',
    borderRadius: 8,
    padding: 10,
  },
});
