"""Collect the small public sources (polite: neutral User-Agent, >= 1 s between calls to a host, cached in data/raw/http/).

  * Greenhouse job API (posting date, department) and Greenhouse board (count of open jobs);
  * SIRENE company register (identity, size band, latest French accounts) - directors are NOT read;
  * DataDome public documentation (Account Protect pages): checks the 'allow' / 'deny' recommendation wording;
  * reference lists used ONLY on simulated traffic: known crawler user-agents (MIT), Googlebot / GPTBot / AWS IP
    ranges, Tor exit list. Only counts are published, never an IP or a prefix.
datadome.co itself answers 403 to scripts (its own bot protection): it is never called here.
Output: data/public/sources_facts.json.  Run:  python src/reference_lists.py
"""
from __future__ import annotations

import json
import sys

from common import PUBLIC, polite_get

GH_JOB = "https://boards-api.greenhouse.io/v1/boards/ddome/jobs/8881607002"
GH_BOARD = "https://boards-api.greenhouse.io/v1/boards/ddome/jobs"
SIRENE = "https://recherche-entreprises.api.gouv.fr/search?q=datadome"
DOCS = "https://docs.datadome.co/docs/"
LISTS = {
    "crawler_user_agents": "https://raw.githubusercontent.com/monperrus/crawler-user-agents/master/crawler-user-agents.json",
    "googlebot_ranges": "https://developers.google.com/static/search/apis/ipranges/googlebot.json",
    "gptbot_ranges": "https://openai.com/gptbot.json",
    "aws_ranges": "https://ip-ranges.amazonaws.com/ip-ranges.json",
    "tor_exits": "https://check.torproject.org/torbulkexitlist",
}


def load_json(url: str) -> dict | list:
    return json.loads(polite_get(url).decode("utf-8"))


def lists() -> dict:
    """Return the reference lists (used by src/simulate_platform.py) - raw values stay in memory / cache only."""
    cua = load_json(LISTS["crawler_user_agents"])
    goog = load_json(LISTS["googlebot_ranges"])
    gpt = load_json(LISTS["gptbot_ranges"])
    aws = load_json(LISTS["aws_ranges"])
    tor = polite_get(LISTS["tor_exits"]).decode("utf-8").split()
    pfx = lambda d: [p.get("ipv4Prefix") or p.get("ipv6Prefix") for p in d["prefixes"]]  # noqa: E731
    return {"crawler_patterns": [c["pattern"] for c in cua], "google": pfx(goog), "gptbot": pfx(gpt),
            "aws": [p["ip_prefix"] for p in aws["prefixes"]], "tor": tor,
            "dates": {"googlebot": goog.get("creationTime"), "gptbot": gpt.get("creationTime"), "aws": aws.get("createDate")}}


def main() -> None:
    facts = {}
    job = load_json(GH_JOB)
    facts["job"] = {"title": job["title"], "location": job["location"]["name"], "first_published": job.get("first_published"),
                    "updated_at": job.get("updated_at"), "departments": [d["name"] for d in job.get("departments", [])],
                    "url": job["absolute_url"], "read_on": "2026-11-26"}
    board = load_json(GH_BOARD)["jobs"]
    facts["open_jobs"] = len(board)
    s = load_json(SIRENE)["results"][0]
    fin = s.get("finances") or {}
    last = max(fin) if fin else None
    facts["sirene"] = {"name": s["nom_complet"], "siren": s["siren"], "created": s["date_creation"],
                       "naf": s["activite_principale"], "size_band_code": s["tranche_effectif_salarie"],
                       "hq_city": s["siege"]["libelle_commune"], "accounts_year": last,
                       "revenue_eur": fin.get(last, {}).get("ca") if last else None,
                       "net_income_eur": fin.get(last, {}).get("resultat_net") if last else None,
                       "read_on": "2026-11-26", "scope": "French legal entity only (not the group)"}
    docs = {}
    for p in ("account-protect-login", "account-protect-registration", "account-protect-dashboard"):
        t = polite_get(DOCS + p).decode("utf-8", "ignore").lower()
        docs[p] = {"bytes": len(t), "mentions_allow": "allow" in t, "mentions_deny": "deny" in t}
    facts["docs"] = docs
    L = lists()
    facts["reference_lists"] = {"crawler_ua_patterns": len(L["crawler_patterns"]), "googlebot_prefixes": len(L["google"]),
                                "gptbot_prefixes": len(L["gptbot"]), "aws_prefixes": len(L["aws"]),
                                "tor_exit_ips": len(L["tor"]), "list_dates": L["dates"], "read_on": "2026-11-26"}
    PUBLIC.mkdir(parents=True, exist_ok=True)
    (PUBLIC / "sources_facts.json").write_text(json.dumps(facts, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: facts[k] for k in ("open_jobs", "reference_lists")}, ensure_ascii=False)[:400])
    print("job:", facts["job"]["first_published"], facts["job"]["departments"], "| sirene:", facts["sirene"]["accounts_year"],
          facts["sirene"]["revenue_eur"], facts["sirene"]["net_income_eur"], facts["sirene"]["size_band_code"])
    print("docs:", docs)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
