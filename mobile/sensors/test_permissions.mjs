import { test } from "node:test";
import assert from "node:assert/strict";
import { ensurePermission, ensureAll } from "./permissions.ts";
import { PERMISSIONS } from "./index.ts";

function fakeBridge(state, log) {
  return {
    async checkPermission(name) {
      return state[name] ?? "denied";
    },
    async requestPermission(name) {
      log.push(name);
      const next = state[name + ":next"] ?? "granted";
      state[name] = next;
      return next;
    },
  };
}

test("grant on request", async () => {
  const log = [];
  const b = fakeBridge({}, log);
  const r = await ensurePermission(b, "camera");
  assert.equal(r.status, "granted");
  assert.equal(r.requested, true);
  assert.deepEqual(log, ["camera"]);
});

test("already granted skips request", async () => {
  const log = [];
  const b = fakeBridge({ microphone: "granted" }, log);
  const r = await ensurePermission(b, "microphone");
  assert.equal(r.status, "granted");
  assert.equal(r.requested, false);
  assert.deepEqual(log, []);
});

test("denied stays denied", async () => {
  const log = [];
  const b = fakeBridge({ contacts: "denied", "contacts:next": "denied" }, log);
  const r = await ensurePermission(b, "contacts");
  assert.equal(r.status, "denied");
  assert.equal(r.requested, true);
});

test("never_ask_again short-circuits", async () => {
  const log = [];
  const b = fakeBridge({ notifications: "never_ask_again" }, log);
  const r = await ensurePermission(b, "notifications");
  assert.equal(r.status, "never_ask_again");
  assert.equal(r.requested, false);
  assert.deepEqual(log, []);
});

test("ensureAll mixed results", async () => {
  const log = [];
  const b = fakeBridge(
    { "location-fine": "granted", calendar: "denied" },
    log
  );
  const rs = await ensureAll(b, ["location-fine", "calendar", "photos"]);
  assert.equal(rs.length, 3);
  assert.equal(rs[0].requested, false);
  assert.equal(rs[1].requested, true);
  assert.equal(rs[2].requested, true);
});

test("permission catalog covers docs/PERMISSIONS.md", () => {
  for (const p of [
    "location-fine",
    "location-coarse",
    "location-background",
    "camera",
    "microphone",
    "notifications",
    "contacts",
    "calendar",
    "photos",
  ]) {
    assert.ok(
      PERMISSIONS.includes(p),
      `catalog missing ${p}`
    );
  }
});
