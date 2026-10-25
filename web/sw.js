// Service Worker – generiert, nicht von Hand bearbeiten
const VERSION = "rezeptbuch-be7d3c2b30c5";
const DATEIEN = ["./", "assets/app.css", "assets/app.js", "assets/daten.js", "einkauf/KW-44-2026.html", "einkauf/KW-45-2026.html", "icons/apple-touch-icon.png", "icons/icon-192.png", "icons/icon-512.png", "index.html", "manifest.webmanifest", "rezept-neu.html", "rezept/beeren-nice-cream.html", "rezept/butter-chicken.html", "rezept/chili-con-carne.html", "rezept/cottage-cheese-mac-and-cheese.html", "rezept/doener-bowl.html", "rezept/erdnuss-kakao-protein-balls.html", "rezept/frikadellen-kartoffelpueree.html", "rezept/fruehstuecks-brownie.html", "rezept/gnocchi-al-forno.html", "rezept/gyros-bowl.html", "rezept/haehnchen-burrito-bowl.html", "rezept/haehnchen-piccata.html", "rezept/heidelbeer-protein-muffins.html", "rezept/kabeljau-curry.html", "rezept/keema-curry-pute.html", "rezept/knoblauch-garnelen-pasta.html", "rezept/koefte-reis.html", "rezept/korean-beef-bowl.html", "rezept/lachs-reis-bowl.html", "rezept/marry-me-chicken.html", "rezept/mie-nudeln-pute.html", "rezept/ofen-lachs-mediterran.html", "rezept/overnight-oats-apfelstrudel.html", "rezept/overnight-oats-cheesecake.html", "rezept/philly-cheesesteak-wrap.html", "rezept/protein-bananenbrot.html", "rezept/protein-crepes.html", "rezept/protein-french-toast.html", "rezept/protein-griessbrei.html", "rezept/protein-joghurt-bowl.html", "rezept/protein-kaiserschmarrn.html", "rezept/protein-lasagne.html", "rezept/protein-milchreis.html", "rezept/protein-mousse-au-chocolat.html", "rezept/protein-pancakes.html", "rezept/protein-waffeln.html", "rezept/puten-souvlaki.html", "rezept/putenschnitzel-airfryer.html", "rezept/quark-auflauf-kirschen.html", "rezept/quarkcreme-banane-zimt.html", "rezept/rindergulasch.html", "rezept/schweinefilet-senf-rahm.html", "rezept/shakshuka-feta.html", "rezept/skyr-cheesecake-im-glas.html", "rezept/skyr-tiramisu-bowl.html", "rezept/smash-burger.html", "rezept/tagliata-hueftsteak.html", "rezept/teriyaki-haehnchen-bowl.html", "rezept/thai-curry-garnelen.html", "rezept/wrap-hack-putenhack.html", "rezepte.html", "woche/KW-44-2026.html", "woche/KW-45-2026.html"];
self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(VERSION).then((c) => c.addAll(DATEIEN)).then(() => self.skipWaiting()));
});
self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys()
    .then((keys) => Promise.all(keys.filter((k) => k !== VERSION).map((k) => caches.delete(k))))
    .then(() => self.clients.claim()));
});
self.addEventListener("fetch", (e) => {
  if (e.request.method !== "GET") return;
  e.respondWith(caches.match(e.request, { ignoreSearch: true })
    .then((r) => r || fetch(e.request).catch(() => caches.match("index.html"))));
});
