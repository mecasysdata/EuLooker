# ╔══════════════════════════════════════════════════════════════════╗
# ║   EuLooker – EC Funding Monitor  |  v7                         ║
# ║   Zmeny v7:                                                     ║
# ║   - Číta users.json, pre každého užívateľa samostatný email     ║
# ║   - Rešpektuje interval: 7 / 14 / 30 dní                       ║
# ║   - AND logika: oblasť + typ organizácie                        ║
# ║   - Vlastné KW užívateľa                                        ║
# ╚══════════════════════════════════════════════════════════════════╝

import requests, json, re, time, os, smtplib
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ── Konfigurácia ──────────────────────────────────────────────────
EMAIL_ODOSIELATEL = "mecasysdata@gmail.com"
EMAIL_HESLO       = os.environ.get('EMAIL_HESLO', 'jeze ycaa dpty cvll')
USERS_SUBOR       = "users.json"
HISTORIA_SUBOR    = "seen_identifiers.json"

# ── Programme ID → názov ──────────────────────────────────────────
PROGRAMME_MAP = {
    "43108390": "Horizon Europe", "44181033": "EDF",
    "43152860": "Digital Europe", "43252405": "LIFE",
    "43251567": "CEF Energy",     "43251589": "CERV",
    "43252368": "ISF",            "43252476": "SMP / COSME",
    "43252517": "ESF+",           "43298916": "Euratom",
    "43353764": "Erasmus+",       "43637601": "PPPA",
    "44416173": "Interreg / I3",
}

# ── Typy organizácií → KW ─────────────────────────────────────────
TYPY_ORG_KW = {
    "SME":                    ["sme","small and medium","smes","eic accelerator","cascade financing","for smes"],
    "Veľký podnik":           ["large enterprise","large company","large industry","for-profit","private company"],
    "Vysoká škola / HEI":     ["higher education","university","academic institution","hei","academia"],
    "Výskumná org. (RTO)":    ["research organisation","research organization","research center","rto","research institute"],
    "Verejný sektor":         ["public body","public authority","municipality","local authority","public administration"],
    "NGO / Asociácia":        ["non-governmental","ngo","association","cluster","foundation","civil society"],
    "NGO / Asociácia / Klaster": ["non-governmental","ngo","association","cluster","foundation","civil society"],
    "Startup / Spin-off":     ["startup","start-up","spin-off","spin-out","deep tech","eic pathfinder","scaleup"],
    "Medzinárodná org.":      ["international organisation","international organization","intergovernmental","multilateral"],
}

# ── Oblasti záujmu → KW (rozšírené) ─────────────────────────────
OBLASTI_KW = {
    "Strojárstvo / Industry 4.0": [
        "industry 4.0","industry 5.0","advanced manufacturing","smart factory",
        "digital twin","industrial automation","cobots","additive manufacturing",
        "3d printing","industrial iot","made in europe","factory of the future",
        "cyber-physical","smart manufacturing","industrial transformation",
        "manufacturing excellence","production technology","automation technology",
        "industrial robot","lean manufacturing","supply chain","quality control",
        "testing facilities","cnc","industrial digitali",
    ],
    "AI / Robotika / Deep Tech": [
        "artificial intelligence","machine learning","robotics","autonomous systems",
        "deep learning","generative ai","computer vision","edge computing",
        "quantum computing","apply ai","neural network","natural language processing",
        "nlp","large language model","trustworthy ai","explainable ai","ai safety",
        "human-robot interaction","embedded ai","foundation model","data-driven",
    ],
    "Zelená energia / Klíma": [
        "renewable energy","green hydrogen","carbon capture","energy storage",
        "solar energy","wind energy","net zero","decarbonisation","energy efficiency",
        "smart grid","clean energy","offshore wind","heat pump","district heating",
        "photovoltaic","battery storage","power grid","electrolysis","biofuel",
        "geothermal","tidal energy","carbon neutral","carbon footprint","emission reduction",
    ],
    "Agro / Bio / Circular": [
        "precision agriculture","smart farming","bioeconomy","bio-based","biodegradable",
        "sustainable packaging","soil health","microbiome","agritech","biomaterial",
        "food security","crop monitoring","bioreactor","fermentation","composting",
        "waste valorisation","biopolymer","green chemistry","plant-based","agroecology",
        "food system","circular bioeconomy",
    ],
    "Zdravie / Medicína / Biotech": [
        "medical device","diagnostics","drug development","clinical trial",
        "personalised medicine","digital health","cancer research","biotechnology",
        "antimicrobial","genomics","vaccine","proteomics","wearable health",
        "mental health","telemedicine","rehabilitation","medical ai","in vitro",
        "cell therapy","rare disease","health data","patient","hospital",
    ],
    "Obrana / Bezpečnosť / Drony": [
        "drone","uav","unmanned","defence","dual-use","counter-drone",
        "border surveillance","cbrn","naval","underwater","security technology","swarm",
        "autonomous underwater","auv","counter-uas","situational awareness",
        "cybersecurity","critical infrastructure","explosive detection",
        "surveillance","radar","military","defense",
    ],
    "Vesmír / Space Tech": [
        "satellite","earth observation","space exploration","copernicus","galileo",
        "new space","remote sensing","space transportation","launch vehicle",
        "reusable rocket","in-orbit","space debris","lunar","space manufacturing",
        "cubesat","nanosatellite","space economy","esa","on-orbit",
    ],
    "Mobilita / Doprava / Smart City": [
        "electric vehicle","autonomous driving","urban mobility","smart city",
        "zero emission vehicle","battery technology","hydrogen vehicle","sustainable transport",
        "charging infrastructure","vehicle to grid","fleet management",
        "micro-mobility","autonomous bus","rail","traffic management",
        "connected vehicle","automated mobility","ccam","logistics","last mile",
    ],
    "Voda / Oceány / Životné prostredie": [
        "water purification","ocean cleaning","marine litter","water quality",
        "blue economy","wastewater","aquaculture","desalination",
        "flood risk","drought","groundwater","ocean acidification",
        "marine ecosystem","plastic recycling","wetland","river restoration",
        "water reuse","water management","marine protected",
    ],
    "Voda / Oceány / Prostredie": [
        "water purification","ocean cleaning","marine litter","water quality",
        "blue economy","wastewater","aquaculture","desalination",
        "flood risk","drought","groundwater","ocean acidification",
        "marine ecosystem","plastic recycling","wetland","water reuse",
    ],
    "Vzdelávanie / Sociálna inovácia": [
        "education technology","vocational training","digital skills","social innovation",
        "edtech","reskilling","upskilling","vocational excellence",
        "lifelong learning","micro-credential","apprenticeship","youth employment",
        "inclusion","disability","rural development","stem education",
        "higher education","skills gap","community","social enterprise",
    ],
}

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# ══════════════════════════════════════════════════════════════════
# POMOCNÉ FUNKCIE
# ══════════════════════════════════════════════════════════════════

def p(msg): print(msg, flush=True)

def _strip_html(text):
    text = re.sub(r'<[^>]+>', ' ', text or '')
    return re.sub(r'\s+', ' ', text).strip()

def _skrat(text, vety=4):
    if not text or len(text) < 40: return text or '—'
    sents = re.split(r'(?<=[.!?])\s+', text.strip())
    sents = [s.strip() for s in sents if len(s.strip()) > 20]
    if not sents: return (text[:500] + '…') if len(text) > 500 else text
    r = ' '.join(sents[:vety])
    return (r[:800] + '…') if len(r) > 800 else r

def _obsahuje(text, slova):
    t = text.lower()
    for w in slova:
        if len(w.split()) > 1:
            if w in t: return True
        else:
            if re.search(r'\b' + re.escape(w) + r's?\b', t): return True
    return False

def _najdi(text, slova):
    t = text.lower()
    found = []
    for w in slova:
        if len(w.split()) > 1:
            if w in t: found.append(w)
        else:
            if re.search(r'\b' + re.escape(w) + r's?\b', t): found.append(w)
    return found

def _nazov_programu(programme_id):
    return PROGRAMME_MAP.get(str(programme_id), str(programme_id))

def _ts_to_dt(ts_ms):
    try:
        return datetime(1970,1,1,tzinfo=timezone.utc) + timedelta(milliseconds=int(ts_ms))
    except:
        return None

# ══════════════════════════════════════════════════════════════════
# INTERVAL LOGIKA
# ══════════════════════════════════════════════════════════════════

def treba_poslat(user):
    """Vráti True ak užívateľovi treba poslať email dnes."""
    interval_raw = user.get('interval', '7dni')

    # Mapovanie intervalov
    if '7' in str(interval_raw):
        dni = 7
    elif '14' in str(interval_raw):
        dni = 14
    elif '30' in str(interval_raw):
        dni = 30
    else:
        dni = 7  # default

    # Dátum posledného emailu
    posledny = user.get('posledny_email')
    if not posledny:
        # Nikdy nedostal email → poslať
        return True, dni

    try:
        dt_posledny = datetime.strptime(posledny, '%Y-%m-%d').date()
        dt_dnes     = datetime.now().date()
        rozdiel     = (dt_dnes - dt_posledny).days
        return rozdiel >= dni, dni
    except:
        return True, dni

# ══════════════════════════════════════════════════════════════════
# API VOLANIA
# ══════════════════════════════════════════════════════════════════

def hladaj_kw(slovo, page=1):
    url = f"https://api.tech.ec.europa.eu/search-api/prod/rest/search?apiKey=SEDIA&text={slovo}&pageSize=50&pageNumber={page}"
    files = {
        "sort"     : (None, json.dumps({"order": "DESC", "field": "startDate"}), "application/json"),
        "query"    : (None, json.dumps({"bool": {"must": [
                        {"terms": {"type": ["1","2","8"]}},
                        {"terms": {"status": ["31094501","31094502"]}}
                     ]}}), "application/json"),
        "languages": (None, json.dumps(["en"]), "application/json"),
    }
    r = requests.post(url, files=files, headers=HEADERS, timeout=30)
    return r.json()

def ziskaj_detail(identifier):
    url = f"https://ec.europa.eu/info/funding-tenders/opportunities/data/topicDetails/{identifier.lower()}.json"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code == 200:
            return r.json().get('TopicDetails', {})
    except:
        pass
    return {}

# ══════════════════════════════════════════════════════════════════
# HĽADANIE VÝZIEV PRE UŽÍVATEĽA
# ══════════════════════════════════════════════════════════════════

def hladaj_pre_uzivatela(user, historia):
    """Hľadá nové výzvy pre konkrétneho užívateľa."""
    email     = user['email']
    typ_org   = user.get('typ_org', '')
    oblasti   = user.get('oblasti', [])
    kw_custom = user.get('kw_custom', [])

    # Zozbieraj KW
    typ_org_kw    = TYPY_ORG_KW.get(typ_org, [])
    oblast_kw_all = []
    search_kw     = []

    for o in oblasti:
        for nazov, kw_list in OBLASTI_KW.items():
            if nazov in o or o in nazov:
                oblast_kw_all.extend(kw_list)
                search_kw.extend(kw_list)
                break

    # Pridaj vlastné KW
    oblast_kw_all.extend(kw_custom)
    search_kw.extend(kw_custom)
    search_kw.extend(typ_org_kw[:3])
    search_kw = list(set(search_kw))

    p(f"  🔍 Hľadám pre {email}: {len(search_kw)} KW, {len(oblasti)} oblastí, typ: {typ_org}")

    # Stiahni výzvy
    vsetky_raw = {}
    for slovo in search_kw:
        try:
            data  = hladaj_kw(slovo)
            total = data.get('totalResults', 0)
            pages = min((total + 49) // 50, 3)
            for page in range(1, pages + 1):
                if page > 1:
                    data = hladaj_kw(slovo, page)
                for hit in data.get('results', []):
                    ident = hit['metadata']['identifier'][0]
                    if ident not in vsetky_raw:
                        vsetky_raw[ident] = hit
            time.sleep(0.3)
        except Exception as e:
            p(f"    ⚠️ Chyba pri '{slovo}': {e}")

    p(f"  Stiahnutých výziev: {len(vsetky_raw)}")

    # Filtruj — len nové (nie v histórii)
    nove_ids = [i for i in vsetky_raw if i not in historia]
    p(f"  Nových (nevidených): {len(nove_ids)}")

    # Klasifikuj s AND filtrom
    vysledky = []
    for ident in nove_ids:
        hit    = vsetky_raw[ident]
        detail = ziskaj_detail(ident)
        if not detail:
            time.sleep(0.2)
            continue

        nazov = hit.get('summary', '')
        popis = _strip_html(detail.get('description', ''))
        ft    = f"{nazov} {popis}".lower()

        ma_oblast = _obsahuje(ft, oblast_kw_all)
        ma_org    = _obsahuje(ft, typ_org_kw) if typ_org_kw else True

        if ma_oblast and ma_org:
            meta     = hit['metadata']
            prog_raw = meta.get('frameworkProgramme', [''])[0]
            vysledky.append({
                'identifier': ident,
                'nazov'     : nazov,
                'programme' : _nazov_programu(prog_raw),
                'status'    : meta.get('status', [''])[0],
                'startDate' : meta.get('startDate', [''])[0][:10],
                'deadline'  : meta.get('deadlineDate', [''])[0][:10],
                'zhrnutie'  : _skrat(popis, 4),
                'link'      : meta.get('url', [''])[0],
                'kw_oblast' : _najdi(ft, oblast_kw_all)[:4],
                'kw_org'    : _najdi(ft, typ_org_kw)[:2],
            })
        time.sleep(0.3)

    p(f"  Relevantných výziev: {len(vysledky)}")

    # Pridaj všetky stiahnuté do histórie (aj tie čo nevyhoveli filtru)
    nova_historia = {**historia, **{i: datetime.now().strftime('%Y-%m-%d') for i in vsetky_raw}}

    return vysledky, nova_historia

# ══════════════════════════════════════════════════════════════════
# EMAIL
# ══════════════════════════════════════════════════════════════════

def odosli_email(user, vysledky, dni):
    email       = user['email']
    typ_org     = user.get('typ_org', '')
    oblasti     = user.get('oblasti', [])
    oblasti_str = ', '.join(oblasti)
    datum       = datetime.now().strftime('%d. %m. %Y')
    interval_sk = f"1× za {dni} dní"
    interval_en = f"every {dni} days"

    if not vysledky:
        predmet = f"EuLooker – {datum} – žiadne nové výzvy / no new calls"
        html = f"""
        <html><body style="font-family:Arial,sans-serif;max-width:780px;margin:auto;padding:24px;">
          <div style="background:#1a2340;color:#fff;padding:20px 24px;border-radius:8px 8px 0 0;">
            <h1 style="margin:0;font-size:20px;">📢 EuLooker – {datum}</h1>
          </div>
          <div style="border:1px solid #dde3ea;border-top:none;padding:24px;border-radius:0 0 8px 8px;">
            <p style="font-size:14px;margin-bottom:8px;">
              Tento týždeň sme pre váš profil nenašli žiadne nové výzvy.
            </p>
            <p style="font-size:13px;color:#555;margin-bottom:20px;">
              <b>Typ org.:</b> {typ_org} &nbsp;·&nbsp; <b>Oblasti:</b> {oblasti_str}
            </p>
            <hr style="border:none;border-top:1px solid #e0e6ef;margin:16px 0;">
            <p style="font-size:14px;margin-bottom:8px;color:#555;">
              No new calls found for your profile this week.
            </p>
            <hr style="border:none;border-top:1px solid #e0e6ef;margin:16px 0 12px;">
            <p style="font-size:12px;color:#888;">
              EuLooker · MecaSys · Interval: {interval_sk} / {interval_en}<br>
              <a href="https://mecasysdata.github.io/EuLooker" style="color:#1565c0;">Zmeniť nastavenia / Change settings</a>
            </p>
          </div>
        </body></html>"""
    else:
        predmet = f"EuLooker – {datum} – {len(vysledky)} nových výziev / {len(vysledky)} new calls"
        bloky = ""
        for v in vysledky:
            kw_text    = ", ".join(v['kw_oblast']) if v['kw_oblast'] else "—"
            kw_org_txt = ", ".join(v['kw_org'])    if v['kw_org']    else "—"
            status_lbl = "🟢 Otvorená / Open" if v['status'] == "31094502" else "🟡 Pripravovaná / Forthcoming"
            bloky += f"""
            <div style="border:1px solid #dde3ea;border-radius:8px;padding:16px 20px;margin-bottom:16px;background:#fafbfc;">
              <h3 style="margin:0 0 6px;color:#1a2340;font-size:14px;">{v['nazov']}</h3>
              <p style="margin:0 0 6px;font-size:12px;color:#555;">
                <b>Program:</b> {v['programme']} &nbsp;|&nbsp;
                {status_lbl} &nbsp;|&nbsp;
                <b>Otvorenie / Opens:</b> {v['startDate']} &nbsp;|&nbsp;
                <b>Uzávierka / Deadline:</b> {v['deadline']}
              </p>
              <p style="margin:0 0 8px;font-size:13px;color:#333;line-height:1.6;">{v['zhrnutie']}</p>
              <p style="margin:0 0 4px;font-size:11px;color:#777;">
                <b>Oblast KW:</b> {kw_text} &nbsp;|&nbsp; <b>Org KW:</b> {kw_org_txt}
              </p>
              <a href="{v['link']}" style="color:#1565c0;font-size:12px;">🔗 {v['link']}</a>
            </div>"""

        html = f"""
        <html><body style="font-family:Arial,sans-serif;max-width:780px;margin:auto;padding:24px;">
          <div style="background:#1a2340;color:#fff;padding:20px 24px;border-radius:8px 8px 0 0;">
            <h1 style="margin:0;font-size:20px;">📢 EuLooker – {datum}</h1>
            <p style="margin:6px 0 0;font-size:14px;opacity:.85;">
              {len(vysledky)} nových výziev · {len(vysledky)} new calls
            </p>
          </div>
          <div style="border:1px solid #dde3ea;border-top:none;padding:24px;border-radius:0 0 8px 8px;">
            <p style="font-size:13px;color:#555;margin-bottom:20px;">
              <b>Typ org.:</b> {typ_org} &nbsp;·&nbsp;
              <b>Oblasti / Areas:</b> {oblasti_str} &nbsp;·&nbsp;
              <b>Interval:</b> {interval_sk} / {interval_en}
            </p>
            {bloky}
            <hr style="border:none;border-top:1px solid #e0e6ef;margin:24px 0 12px;">
            <p style="font-size:12px;color:#888;">
              EuLooker · MecaSys ·
              <a href="https://mecasysdata.github.io/EuLooker" style="color:#1565c0;">mecasysdata.github.io/EuLooker</a>
            </p>
          </div>
        </body></html>"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = predmet
    msg["From"]    = EMAIL_ODOSIELATEL
    msg["To"]      = email
    msg.attach(MIMEText(html, "html", "utf-8"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_ODOSIELATEL, EMAIL_HESLO)
            server.sendmail(EMAIL_ODOSIELATEL, email, msg.as_string())
        p(f"  ✅ Email odoslaný na {email} ({len(vysledky)} výziev)")
        return True
    except Exception as e:
        p(f"  ❌ Chyba emailu pre {email}: {e}")
        return False

# ══════════════════════════════════════════════════════════════════
# HISTÓRIA
# ══════════════════════════════════════════════════════════════════

def nacitaj_historiu():
    if os.path.exists(HISTORIA_SUBOR):
        with open(HISTORIA_SUBOR, 'r') as f:
            data = json.load(f)
            if isinstance(data, list):
                return {i: "unknown" for i in data}
            return data
    return {}

def uloz_historiu(historia):
    with open(HISTORIA_SUBOR, 'w') as f:
        json.dump(historia, f, indent=2)

def nacitaj_users():
    if os.path.exists(USERS_SUBOR):
        with open(USERS_SUBOR, 'r') as f:
            return json.load(f)
    return []

def uloz_users(users):
    with open(USERS_SUBOR, 'w') as f:
        json.dump(users, f, indent=2, ensure_ascii=False)

# ══════════════════════════════════════════════════════════════════
# HLAVNÝ TOK
# ══════════════════════════════════════════════════════════════════

def main():
    p("=" * 60)
    p(f"EuLooker v7 – {datetime.now().strftime('%d.%m.%Y %H:%M')}")
    p("=" * 60)

    users   = nacitaj_users()
    historia = nacitaj_historiu()

    p(f"\n👥 Užívateľov celkom: {len(users)}")

    if not users:
        p("⚠️  Žiadni užívatelia v users.json")
        return

    dnes          = datetime.now().date()
    spracovanych  = 0
    preskocených  = 0
    nova_historia = dict(historia)

    for user in users:
        email = user.get('email', '?')
        p(f"\n{'─'*50}")
        p(f"👤 {email}")

        # Skontroluj interval
        poslat, dni = treba_poslat(user)
        if not poslat:
            posledny = user.get('posledny_email', '?')
            p(f"  ⏭️  Preskakujem — posledný email: {posledny}, interval: {dni} dní")
            preskocených += 1
            continue

        p(f"  📨 Posielajú sa výzvy (interval: {dni} dní)")

        # Hľadaj výzvy
        vysledky, nova_historia = hladaj_pre_uzivatela(user, nova_historia)

        # Pošli email
        uspech = odosli_email(user, vysledky, dni)

        if uspech:
            # Aktualizuj dátum posledného emailu
            user['posledny_email'] = dnes.strftime('%Y-%m-%d')
            spracovanych += 1

    # Ulož aktualizovaných users a históriu
    uloz_users(users)
    uloz_historiu(nova_historia)

    p(f"\n{'='*60}")
    p(f"✅ Hotovo! Spracovaných: {spracovanych}, Preskočených: {preskocených}")
    p(f"História: {len(nova_historia)} výziev")
    p("=" * 60)

if __name__ == "__main__":
    main()
