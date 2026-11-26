# Sources (all read on 26 Nov 2026)

| Source | URL | Used for | Terms |
|---|---|---|---|
| DataDome job posting, Fraud Analyst (Greenhouse job board API) | https://boards-api.greenhouse.io/v1/boards/ddome/jobs/8881607002 | missions, requirements, department (Threat Research), first published 13 Oct 2026 | public posting |
| DataDome Greenhouse board | https://boards-api.greenhouse.io/v1/boards/ddome/jobs | 24 open jobs | public |
| DataDome, State of Bot & Agent Security Report 2026 (web page, read in a browser; the PDF behind a form was not requested) | https://datadome.co/resources/bot-and-agent-security-report/ | figures quoted "as stated by DataDome" | quoted, not reused |
| DataDome, account takeover solution page (read in a browser) | https://datadome.co/solutions/account-takeover/ | vocabulary (signals listed by DataDome) | quoted, not reused |
| DataDome public documentation, Account Protect login / registration / dashboard | https://docs.datadome.co/docs/account-protect-login | recommendation allow / deny, the application keeps the final decision | public documentation |
| French company register (SIRENE, recherche-entreprises API) | https://recherche-entreprises.api.gouv.fr/search?q=datadome | SIREN 811 474 949, created 11 May 2015, NAF 62.02A, Paris, 100-199 employees band, 2024 French-entity accounts | Licence Ouverte (Etalab) |
| Login Data Set for Risk-Based Authentication | https://zenodo.org/records/6782156 | 31,269,264 synthesized logins, Feb 2020 - Feb 2021 | DOI 10.5281/zenodo.6782156, CC BY 4.0 |
| Web robot detection - Server logs | https://zenodo.org/records/3477932 | 67,352 labelled sessions, March 2018 (feature files only) | DOI 10.5281/zenodo.3477932, CC BY 4.0 |
| crawler-user-agents (known crawler patterns) | https://github.com/monperrus/crawler-user-agents | 1,510 patterns (updated 25 Nov 2026) | MIT |
| Googlebot IP ranges | https://developers.google.com/static/search/apis/ipranges/googlebot.json | 317 prefixes (creationTime 25 Nov 2026) | published by Google |
| GPTBot IP ranges | https://openai.com/gptbot.json | 18 prefixes (creationTime 22 Sep 2026) | published by OpenAI |
| AWS IP ranges | https://ip-ranges.amazonaws.com/ip-ranges.json | 10,777 prefixes (26 Nov 2026) | published by AWS |
| Tor bulk exit list | https://check.torproject.org/torbulkexitlist | 1,259 exit addresses | published by the Tor Project |

## Facts as stated by DataDome (report 2026 web page, read 26 Nov 2026)
- July 2025 - June 2026: bad bot traffic grew about 124 %, more than 9 times faster than human traffic; AI traffic +82.3 %.
- Scraping: 70.9 % of bad bot traffic, +185.2 %.
- Meta-affiliated bots 46.3 % and OpenAI-affiliated bots 34.6 % of identified AI crawler traffic.
- Fake account creation +34.5 %; credential stuffing "cyclical rather than declining".
- Of 20,000+ websites tested, 65.3 % stopped none of 10 bot types and 2.4 % stopped all (8.4 % in 2024, 2.8 % in 2025).

## Facts from the job posting (as stated by DataDome)
5 trillion signals per day, more than 20,000 attacks stopped per second, 30+ points of presence, 80+ integrations, named a Leader
in a 2026 analyst evaluation of bot and agent trust management.

## Company register (SIRENE)
DATADOME, French legal entity: 2024 revenue EUR 14,030,274, net result EUR -10,532,052 (French entity only, not the group).
Directors are not read nor stored.

## Collection rules followed
Official APIs and files only; at most one request per second per host; each file downloaded once and cached locally; neutral
User-Agent `datadome-case-study/1.0`. `datadome.co` answers 403 to scripts (its own bot protection): it was never called by a
script, only read in a browser. No form, account, payment or message. The local robot lab only talks to 127.0.0.1.
