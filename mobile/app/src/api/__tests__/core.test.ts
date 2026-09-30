import {createCoreClient, FetchFn} from '../core';

describe('core client', () => {
  it('posts answer requests with text body', async () => {
    const calls: Array<{url: string; body?: string}> = [];
    const stub: FetchFn = async (url, init) => {
      calls.push({url, body: init?.body});
      return {
        json: async () => ({
          question: 'hi',
          routed_search: false,
          evidence: [],
          verify: {pass: true, reason: 'direct'},
          response: 'hello',
        }),
      };
    };
    const client = createCoreClient('http://test', stub);
    const res = await client.answer('hi');
    expect(calls).toHaveLength(1);
    expect(calls[0].url).toBe('http://test/answer');
    expect(JSON.parse(calls[0].body ?? '{}')).toEqual({text: 'hi'});
    expect(res.response).toBe('hello');
  });

  it('posts nearby search with lat/lng/radius', async () => {
    const calls: Array<{url: string; body?: string}> = [];
    const stub: FetchFn = async (url, init) => {
      calls.push({url, body: init?.body});
      return {json: async () => []};
    };
    const client = createCoreClient('http://test', stub);
    await client.nearbySearch(39.9, 116.4, 1000, '理发');
    expect(calls[0].url).toBe('http://test/poi/nearby');
    expect(JSON.parse(calls[0].body ?? '{}')).toEqual({
      lat: 39.9,
      lng: 116.4,
      radius_m: 1000,
      keywords: '理发',
    });
  });
});
