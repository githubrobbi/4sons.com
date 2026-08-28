// The front door for the domain: the landing page is served from ./site (assets),
// every section is its own Cloudflare Pages project owned by its author, proxied by path.
import { resolve, parseEnabled, TITLES } from "./routes.js";

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const enabled = parseEnabled(env.SECTIONS_ENABLED);
    if (url.pathname === "/sections.json") {
      const list = [...enabled].filter((s) => s in TITLES).map((s) => ({ path: `/${s}/`, title: TITLES[s] }));
      return new Response(JSON.stringify(list), { headers: { "content-type": "application/json", "cache-control": "no-store" } });
    }
    const route = resolve(url.pathname, enabled);
    if (route.kind === "disabled") {
      return new Response(`<!doctype html><meta charset="utf-8"><title>Not published</title><p style="font:16px system-ui;margin:3rem">This page is not published. <a href="/">Back</a></p>`, { status: 404, headers: { "content-type": "text/html; charset=utf-8", "cache-control": "no-store" } });
    }
    if (route.kind === "redirect") return Response.redirect(url.origin + route.to + url.search, 301);
    if (route.kind === "proxy") {
      // A section without a trailing slash would break its relative links: normalize once.
      if (!url.pathname.endsWith("/") && !url.pathname.split("/").pop().includes(".")) {
        return Response.redirect(url.origin + url.pathname + "/" + url.search, 301);
      }
      const origin = `https://${route.project}.pages.dev${route.rest}${url.search}`;
      const upstream = await fetch(origin, { method: request.method, headers: { accept: request.headers.get("accept") ?? "*/*" }, cf: { cacheTtl: 300 } });
      const headers = new Headers(upstream.headers);
      headers.delete("set-cookie");
      return new Response(upstream.body, { status: upstream.status, headers });
    }
    if (route.kind === "landing" || route.kind === "unknown") return env.ASSETS.fetch(request);
    return new Response("not found", { status: 404 });
  },
};
