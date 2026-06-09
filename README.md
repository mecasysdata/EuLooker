# EuLooker — EU Grants Monitor

Automatický monitoring EU výziev z EC Funding & Tenders portálu.
Každý pondelok prehľadá 200+ programov a pošle email len s relevantnými výzvami.

## Čo to robí

- Prehľadáva všetky programy EC portálu (Horizon, EDF, LIFE, EIC, Digital Europe, Erasmus+...)
- Filtruje len Open + Forthcoming výzvy
- Hľadá kľúčové slová v plnom texte každej výzvy
- Posiela len nové výzvy — tie čo ste už dostali sa neposielajú znova
- Filtruje len výzvy relevantné pre SME

## Súbory

| Súbor | Popis |
|---|---|
| `index.html` | Landing page + konfigurátor |
| `eu_grants_agent.py` | Hlavný Python skript |
| `seen_identifiers.json` | História odoslaných výziev |
| `.github/workflows/eu_grants.yml` | GitHub Actions — spúšťa sa každý pondelok |

## Inštalácia

1. Forkni tento repozitár
2. Uprav `eu_grants_agent.py` — nastav `EMAIL_PRIJEMCA`
3. Zapni GitHub Pages: `Settings → Pages → main → / (root)`
4. Nastav workflow permissions: `Settings → Actions → General → Read and write permissions`
5. Spusti prvý beh: `Actions → EU Grants Agent → Run workflow`

## Tech stack

- Python 3.11
- GitHub Actions (scheduler)
- GitHub Pages (frontend)
- Gmail SMTP (email)
- EC Search API (data)

## Zdroj dát

[EC Funding & Tenders Portal](https://ec.europa.eu/info/funding-tenders/opportunities/portal)
