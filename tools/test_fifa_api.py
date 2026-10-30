#!/usr/bin/env python3
"""Teste les endpoints FIFA Virtual et affiche la structure des données reçues.

Usage : python3 tools/test_fifa_api.py [nb_matchs_a_detailler]
Les réponses brutes sont enregistrées dans tools/api_dump/.
"""
import gzip
import json
import os
import sys
import urllib.request

BASE = "https://22bet.com/LiveFeed"
LIST_URL = f"{BASE}/Get1x2_VZip?sports=85&count=100&lng=en&mode=4&cyberFlag=1"
DETAIL_URL = BASE + "/GetGameZip?id={id}&lng=en"
DUMP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "api_dump")


def fetch(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read()
        if resp.headers.get("Content-Encoding") == "gzip" or raw[:2] == b"\x1f\x8b":
            raw = gzip.decompress(raw)
        return resp.status, json.loads(raw)


def describe(value, path="", depth=0, max_depth=6, seen=None):
    """Imprime chaque clé avec son type et un exemple de valeur (sans doublons de chemin)."""
    seen = set() if seen is None else seen
    if depth > max_depth:
        return
    if isinstance(value, dict):
        for k, v in value.items():
            p = f"{path}.{k}" if path else k
            if p not in seen:
                seen.add(p)
                sample = "" if isinstance(v, (dict, list)) else f" = {str(v)[:60]!r}"
                print(f"{'  ' * depth}{p} ({type(v).__name__}){sample}")
            describe(v, p, depth + 1, max_depth, seen)
    elif isinstance(value, list):
        for item in value[:3]:
            describe(item, path + "[]", depth, max_depth, seen)


def save(name, data):
    os.makedirs(DUMP_DIR, exist_ok=True)
    with open(os.path.join(DUMP_DIR, name), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main():
    n_details = int(sys.argv[1]) if len(sys.argv) > 1 else 3

    print(f"== LISTE : {LIST_URL}")
    status, data = fetch(LIST_URL)
    save("list.json", data)
    games = data.get("Value") or []
    print(f"HTTP {status} | Success={data.get('Success')} | {len(games)} matchs\n")
    describe(data)

    for g in games[:n_details]:
        url = DETAIL_URL.format(id=g.get("N"))
        print(f"\n== DÉTAIL : {g.get('O1')} vs {g.get('O2')} | I={g.get('I')} N={g.get('N')}")
        try:
            status, detail = fetch(url)
        except Exception as e:  # 404, timeout...
            print(f"ÉCHEC : {e}")
            continue
        save(f"detail_{g.get('N')}.json", detail)
        value = detail.get("Value") or {}
        markets = value.get("GE") or []
        n_odds = sum(len(c) for m in markets for c in m.get("E", []))
        print(f"HTTP {status} | {len(markets)} groupes de marchés | {n_odds} cotes")
        describe(detail)


if __name__ == "__main__":
    main()
