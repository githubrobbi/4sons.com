import test from "node:test";
import assert from "node:assert/strict";
import { resolve, parseEnabled, ROUTES, ALIASES, TITLES } from "./routes.js";

test("the landing is the root", () => assert.equal(resolve("/").kind, "landing"));
test("every route proxies with the rest of the path", () => {
  for (const [head, project] of Object.entries(ROUTES)) {
    assert.deepEqual(resolve(`/${head}/a/b.html`), { kind: "proxy", project, rest: "/a/b.html" });
  }
});
test("aliases redirect into their section", () => {
  for (const [alias, target] of Object.entries(ALIASES)) {
    assert.equal(resolve(`/${alias}/x`).to, `/${target}/x`);
    assert.ok(target in ROUTES, `alias ${alias} points at a real section`);
  }
});
test("case does not matter", () => assert.equal(resolve("/" + Object.keys(ROUTES)[0].toUpperCase() + "/").kind, "proxy"));
test("unknown paths fall to the landing assets (404 there)", () => assert.equal(resolve("/nope/").kind, "unknown"));

test("a section that is not enabled answers disabled, alias included", () => {
  const first = Object.keys(ROUTES)[0];
  const none = parseEnabled("");
  assert.deepEqual(resolve(`/${first}/`, none), { kind: "disabled", section: first });
  for (const alias of Object.keys(ALIASES)) assert.equal(resolve(`/${alias}/`, none).kind, "disabled");
  const only = parseEnabled(` ${first.toUpperCase()} , nope `);
  assert.equal(resolve(`/${first}/`, only).kind, "proxy");
});
test("every route has a title for the landing", () => {
  for (const head of Object.keys(ROUTES)) assert.ok(head in TITLES, head);
});
