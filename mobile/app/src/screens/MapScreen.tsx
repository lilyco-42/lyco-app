import React, {useState} from 'react';
import {
  Button,
  FlatList,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import {createCoreClient, Poi, RankedShop} from '../api/core';

const client = createCoreClient();

interface Row {
  title: string;
  sub: string;
  detail: string;
}

function toRows(items: Array<Poi | RankedShop>): Row[] {
  return items.map(item => {
    if ('distance' in item) {
      return {
        title: item.name,
        sub: item.address,
        detail: `${item.distance} 米`,
      };
    }
    return {title: item.name, sub: item.address, detail: item.summary};
  });
}

/** TODO: replace placeholder with react-native-maps once native deps land. */
function MapPlaceholder({pois}: {pois: Poi[]}) {
  return (
    <View style={styles.map}>
      <Text>地图占位（{pois.length} 个 POI）── 接入 react-native-maps 后替换</Text>
    </View>
  );
}

export function MapScreen() {
  const [pois, setPois] = useState<Poi[]>([]);
  const [ranked, setRanked] = useState<RankedShop[]>([]);
  const [busy, setBusy] = useState(false);

  // TODO: replace fixed coords with sensors/location permission flow.
  async function searchNearby() {
    if (busy) {
      return;
    }
    setBusy(true);
    try {
      const list = await client.nearbySearch(39.989643, 116.481028, 1000);
      setPois(list);
      setRanked([]);
    } finally {
      setBusy(false);
    }
  }

  async function rank() {
    if (busy || pois.length === 0) {
      return;
    }
    setBusy(true);
    try {
      setRanked(await client.rankShops(pois));
    } finally {
      setBusy(false);
    }
  }

  return (
    <View style={styles.container}>
      <MapPlaceholder pois={pois} />
      <View style={styles.row}>
        <Button
          title="搜身边 1km"
          onPress={searchNearby}
          disabled={busy}
        />
        <Button
          title="哪家好"
          onPress={rank}
          disabled={busy || pois.length === 0}
        />
      </View>
      <FlatList
        data={toRows(ranked.length > 0 ? ranked : pois)}
        keyExtractor={(item, i) => `${item.title}-${i}`}
        renderItem={({item}) => (
          <View style={styles.card}>
            <Text style={styles.name}>{item.title}</Text>
            <Text>{item.sub}</Text>
            <Text>{item.detail}</Text>
          </View>
        )}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {flex: 1, padding: 12},
  map: {
    height: 180,
    backgroundColor: '#e5e7eb',
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 8,
  },
  row: {flexDirection: 'row', gap: 8, marginBottom: 8},
  card: {
    padding: 10,
    borderWidth: 1,
    borderColor: '#e5e7eb',
    borderRadius: 8,
    marginBottom: 8,
  },
  name: {fontWeight: 'bold'},
});
