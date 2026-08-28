// The routing table: first path segment -> Cloudflare Pages project (its *.pages.dev origin).
// Add a section: one line here, one Pages project, one repo owned by whoever writes it.
export const ROUTES = {
  "david": "4sons-david",
  "son2": "4sons-son2",
  "son3": "4sons-son3",
  "son4": "4sons-son4"
};
// Aliases 301 to their target section.
export const ALIASES = {};

// Section titles for the landing page's list (served at /sections.json).
export const TITLES = {"david": "David", "son2": "Son 2", "son3": "Son 3", "son4": "Son 4"};

// The switch: `enabled` is the set of section names currently published
// (the Worker reads it from the SECTIONS_ENABLED variable, editable in the
// Cloudflare dashboard without a deploy). A section that exists but is not
// enabled answers "not published" and is absent from the landing.
export function parseEnabled(value) {
  return new Set(String(value ?? "").split(",").map((s) => s.trim().toLowerCase()).filter(Boolean));
}

export function resolve(pathname, enabled = new Set(Object.keys(ROUTES))) {
  const parts = pathname.split("/");
  const head = (parts[1] || "").toLowerCase();
  if (head === "") return { kind: "landing" };
  if (head in ALIASES) {
    if (!enabled.has(ALIASES[head])) return { kind: "disabled", section: ALIASES[head] };
    return { kind: "redirect", to: "/" + ALIASES[head] + "/" + parts.slice(2).join("/") };
  }
  if (head in ROUTES) {
    if (!enabled.has(head)) return { kind: "disabled", section: head };
    return { kind: "proxy", project: ROUTES[head], rest: "/" + parts.slice(2).join("/") };
  }
  return { kind: "unknown" };
}
