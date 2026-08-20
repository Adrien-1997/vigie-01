"""Collecte les logos des medias du perimetre, une fois, vers frontend/src/assets/logos/.

Outil d'operateur, comme scripts/daily_run.py : il n'est importe par aucun noeud du pipeline et ne
part pas en production. Il ne consomme aucun budget LLM.

Pourquoi hors ligne plutot qu'un `<img src="https://.../favicon.ico">` a l'affichage : servir les
icones depuis les sites d'origine ferait partir dix-sept requetes vers des tiers a chaque ouverture
du digest (dont TASS, CGTN, Mehr News), donnerait a ces tiers l'IP du lecteur, et livrerait une
interface qui se degrade quand un site est en panne. Les fichiers sont donc recuperes une fois,
versionnes avec le front, et servis par Vite comme n'importe quel asset.

Le nom de fichier est le slug du nom de source (`backend/config.py`). frontend/src/lib/logos.ts
applique exactement la meme regle de slug et recupere le lot via import.meta.glob : aucun manifeste
a tenir synchrone, une source sans fichier retombe simplement sur son monogramme.

    python -m scripts.fetch_logos            # sources manquantes seulement
    python -m scripts.fetch_logos --force    # retelecharge tout
    python -m scripts.fetch_logos --list     # ce qui est present / manquant, sans reseau
"""

from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen

from backend.config import SOURCES, Source

LOGO_DIR = Path(__file__).resolve().parent.parent / "frontend" / "src" / "assets" / "logos"

# Les flux qui ne sont pas heberges par le media qu'ils publient : l'icone du domaine du flux
# serait celle de Feedburner, pas celle de la redaction.
SITE_OVERRIDES = {
    "Breaking Defense": "https://breakingdefense.com/",
}

# Un format que le navigateur sait afficher dans <img>, et rien d'autre : un .webmanifest ou un
# .json declares en rel="icon" existent dans la nature et ne rendraient rien.
EXTENSIONS = {
    "image/svg+xml": ".svg",
    "image/png": ".png",
    "image/x-icon": ".ico",
    "image/vnd.microsoft.icon": ".ico",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
}
ALLOWED_SUFFIXES = {".svg", ".png", ".ico", ".jpg", ".jpeg", ".webp"}

# Au-dela, ce n'est plus une icone : certains sites declarent en rel="icon" une image d'entete de
# plusieurs centaines de kilo-octets, qu'on ne veut pas versionner pour l'afficher en 22 px.
MAX_BYTES = 400_000

USER_AGENT = "vigie-01 logo collector (+https://github.com/adrien-morel/vigie-01)"
TIMEOUT = 15


def slugify(name: str) -> str:
    """Doit rester le miroir exact de `slugify` dans frontend/src/lib/logos.ts."""
    folded = unicodedata.normalize("NFD", name)
    folded = "".join(c for c in folded if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", "-", folded.lower()).strip("-")


class IconLinkParser(HTMLParser):
    """Releve les <link rel="...icon..."> et le nom du site. On s'arrete a </head> : le corps de
    page n'en contient pas, et certains flux d'actualite pesent plusieurs mega-octets."""

    def __init__(self) -> None:
        super().__init__()
        self.icons: list[tuple[str, str, str]] = []  # (href, rel, sizes)
        self.done = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "link":
            return
        a = {k.lower(): (v or "") for k, v in attrs}
        rel = a.get("rel", "").lower()
        if "icon" in rel and a.get("href"):
            self.icons.append((a["href"], rel, a.get("sizes", "")))

    def handle_endtag(self, tag: str) -> None:
        if tag == "head":
            self.done = True


def fetch(url: str) -> tuple[bytes, str]:
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    with urlopen(request, timeout=TIMEOUT) as response:  # noqa: S310 - URLs issues de config.py
        return response.read(MAX_BYTES + 1), response.headers.get("Content-Type", "")


def icon_rank(href: str, rel: str, sizes: str) -> tuple[int, int]:
    """Le meilleur candidat d'abord : vectoriel, puis la plus grande taille declaree. Une icone de
    16 px etiree dans un carre de 22 px est floue sur un ecran a densite double."""
    suffix = Path(urlsplit(href).path).suffix.lower()
    vector = 2 if suffix == ".svg" else 1 if "apple-touch" in rel else 0
    largest = 0
    for token in sizes.lower().split():
        if "x" in token:
            head = token.split("x")[0]
            if head.isdigit():
                largest = max(largest, int(head))
    return (vector, largest)


def discover(site: str) -> list[str]:
    """Candidats d'icone pour un site, du plus prometteur au repli conventionnel."""
    try:
        html, _ = fetch(site)
    except Exception as exc:  # noqa: BLE001 - un site injoignable ne doit pas arreter le lot
        print(f"    page d'accueil injoignable ({exc.__class__.__name__}) - repli sur /favicon.ico")
        return [urljoin(site, "/favicon.ico")]

    parser = IconLinkParser()
    try:
        parser.feed(html.decode("utf-8", errors="replace"))
    except Exception:  # noqa: BLE001 - HTML malforme : on garde ce qui a ete releve avant l'erreur
        pass

    ranked = sorted(parser.icons, key=lambda i: icon_rank(*i), reverse=True)
    candidates = [urljoin(site, href) for href, _, _ in ranked]
    candidates.append(urljoin(site, "/favicon.ico"))
    seen: set[str] = set()
    return [c for c in candidates if not (c in seen or seen.add(c))]


def suffix_for(url: str, content_type: str) -> str | None:
    from_type = EXTENSIONS.get(content_type.split(";")[0].strip().lower())
    if from_type:
        return from_type
    suffix = Path(urlsplit(url).path).suffix.lower()
    return suffix if suffix in ALLOWED_SUFFIXES else None


def collect(name: str, site: str) -> Path | None:
    for url in discover(site):
        try:
            data, content_type = fetch(url)
        except Exception as exc:  # noqa: BLE001 - on essaie simplement le candidat suivant
            print(f"    {url} - {exc.__class__.__name__}")
            continue
        if not data:
            continue
        if len(data) > MAX_BYTES:
            print(f"    {url} - ignore, plus de {MAX_BYTES // 1000} ko")
            continue
        suffix = suffix_for(url, content_type)
        if suffix is None:
            print(f"    {url} - type non affichable ({content_type or 'inconnu'})")
            continue
        target = LOGO_DIR / f"{slugify(name)}{suffix}"
        for stale in LOGO_DIR.glob(f"{slugify(name)}.*"):
            stale.unlink()
        target.write_bytes(data)
        print(f"    [ok] {target.name} ({len(data) // 1000 or 1} ko) <- {url}")
        return target
    return None


def site_of(source: Source) -> str:
    """Le site du media, pas celui du flux : un flux Feedburner rendrait l'icone de Feedburner."""
    parts = urlsplit(source.url)
    return SITE_OVERRIDES.get(source.name) or f"{parts.scheme}://{parts.netloc}/"


def existing(name: str) -> Path | None:
    return next(iter(sorted(LOGO_DIR.glob(f"{slugify(name)}.*"))), None)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="retelecharge meme si le fichier existe")
    parser.add_argument("--list", action="store_true", help="etat local, sans acces reseau")
    args = parser.parse_args()

    LOGO_DIR.mkdir(parents=True, exist_ok=True)
    sites = {s.name: site_of(s) for s in SOURCES}

    if args.list:
        for name in sites:
            found = existing(name)
            print(f"{'[ok]' if found else '[--]'} {name:42} {found.name if found else 'monogramme'}")
        return 0

    missing: list[str] = []
    for name, site in sites.items():
        found = existing(name)
        if found and not args.force:
            print(f"   {name} - deja present ({found.name})")
            continue
        print(f"-> {name} - {site}")
        if collect(name, site) is None:
            missing.append(name)
            print("    aucun logo exploitable - la carte affichera un monogramme")

    print(f"\n{len(sites) - len(missing)}/{len(sites)} sources avec logo.")
    if missing:
        print("Sans logo : " + ", ".join(missing))
    return 0


if __name__ == "__main__":
    sys.exit(main())
