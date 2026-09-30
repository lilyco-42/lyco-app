/** Typed client stubs matching the Python backend shapes.
 * TODO: wire baseURL to the on-device core server (see core/loop.py answer(),
 * services/poi nearby_search(), services/reviews rank_shops()).
 * Transport is injectable so tests run without network.
 */

export interface AnswerResult {
  question: string;
  routed_search: boolean;
  evidence: string[];
  verify: { pass: boolean; reason: string };
  response: string;
}

export interface Poi {
  name: string;
  address: string;
  location: string;
  distance: string;
  tel: string;
}

export interface RankedShop {
  name: string;
  address: string;
  reason: string;
  summary: string;
}

export type FetchFn = (
  url: string,
  init?: { method?: string; body?: string }
) => Promise<{ json: () => Promise<unknown> }>;

const defaultFetch: FetchFn = (url, init) =>
  fetch(url, {
    method: init?.method ?? 'GET',
    body: init?.body,
    headers: { 'Content-Type': 'application/json' },
  }) as Promise<{ json: () => Promise<unknown> }>;

/** TODO: point at the on-device core server once mobile/inference lands. */
export const DEFAULT_BASE_URL = 'http://127.0.0.1:8080';

export function createCoreClient(
  baseURL: string = DEFAULT_BASE_URL,
  fetchFn: FetchFn = defaultFetch
) {
  async function post<T>(path: string, body: unknown): Promise<T> {
    const res = await fetchFn(`${baseURL}${path}`, {
      method: 'POST',
      body: JSON.stringify(body),
    });
    return (await res.json()) as T;
  }

  return {
    answer: (text: string) => post<AnswerResult>('/answer', { text }),
    nearbySearch: (
      lat: number,
      lng: number,
      radiusM: number = 1000,
      keywords?: string
    ) =>
      post<Poi[]>('/poi/nearby', {
        lat,
        lng,
        radius_m: radiusM,
        keywords,
      }),
    rankShops: (pois: Poi[]) => post<RankedShop[]>('/reviews/rank', { pois }),
  };
}

export type CoreClient = ReturnType<typeof createCoreClient>;
