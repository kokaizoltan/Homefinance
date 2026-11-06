# HomeFinance – Otthoni bevételek és kiadások nyilvántartása

Modern, reszponzív, magyar nyelvű webalkalmazás háztartási pénzügyek kezelésére.
A projekt a `gyors_mesterprompt_HG.txt` követelményei alapján készült, működő és
automatizált tesztekkel ellenőrzött Django-alkalmazás.

## Fő funkciók

- Regisztráció, bejelentkezés és kijelentkezés e-mail-címmel.
- Bevételek és kiadások rögzítése, módosítása, törlése.
- Felhasználónkénti bevételi és kiadási kategóriák kezelése.
- Tranzakciók listázása, keresése és szűrése dátum, típus, kategória és leírás szerint.
- Havi bevétel-, kiadás- és egyenlegösszesítés a vezérlőpulton.
- Kategóriánkénti kimutatások, százalékos megoszlás és grafikonok.
- 6 és 12 hónapos trendgrafikon.
- Reszponzív Bootstrap felület, asztali gépen, tableten és mobilon.
- Világos visszajelzések sikeres és sikertelen műveleteknél.
- Adminisztrációs felület (`/admin/`).

## Technológiai stack

| Réteg | Technológia |
| --- | --- |
| Backend | Python 3.12+ (fejlesztve: Python 3.14), Django 6.1 |
| Adatbázis | SQLite (fejlesztés) / PostgreSQL (éles) |
| Frontend | HTML, CSS, JavaScript, Bootstrap 5.3, Bootstrap Icons, Chart.js 4 |
| Konfiguráció | django-environ, `.env` fájl |
| Tesztelés | Django `TestCase` |

## Projektstruktúra

```text
K Z - HOMEFINANCE/
├── manage.py
├── requirements.txt
├── .env.example              # környezeti változók mintája
├── .env                      # helyi fejlesztői konfiguráció (gitignore)
├── .gitignore
├── README.md
├── homefinance/              # Django projekt
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
├── finance/                  # Django alkalmazás
│   ├── models.py             # User, Category, Transaction
│   ├── forms.py              # űrlapok és validáció
│   ├── views.py              # nézetek
│   ├── services.py           # összesítések, kimutatások
│   ├── urls.py
│   ├── admin.py
│   ├── migrations/
│   ├── management/commands/seed_demo.py
│   ├── templatetags/finance_extras.py
│   ├── templates/finance/    # alkalmazás sablonjai
│   └── tests/                # 94 automatizált teszt
├── templates/                # base.html, 403.html, 404.html
└── static/
    ├── css/style.css
    └── js/app.js
```

## Telepítés és indítás

### 1. Virtuális környezet és függőségek

```bash
cd "/home/hp/Desktop/K Z - HOMEFINANCE"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

> A `.venv` virtuális környezet ebben a projektmappában már létre van hozva, és
> a `requirements.txt` összes függősége telepítve van benne (Django 6.1.3,
> django-environ, psycopg). Indítás előtt csak aktiválni kell:
>
> ```bash
> source .venv/bin/activate
> ```
>
> Aktíválás nélkül is futtatható: `.venv/bin/python manage.py runserver`.

### 2. Környezeti változók

A repóban lévő `.env` fejlesztésre kész. Új gépen:

```bash
cp .env.example .env
```

Fejlesztéshez elegendő:

```env
DEBUG=True
SECRET_KEY=django-insecure-dev-only-csere-elesben
ALLOWED_HOSTS=localhost,127.0.0.1
```

Ha a `DATABASE_URL` nincs megadva, a projekt a gyökérkönyvtárban lévő
`db.sqlite3` fájlt használja.

### 3. Adatbázis-migrációk

```bash
python manage.py migrate
```

### 4. (Opcionális) Demó adatok

```bash
python manage.py seed_demo
```

Ez létrehozza a következő fiókot három hónapnyi mintaadattal:

- **E-mail:** `demo@homefinance.hu`
- **Jelszó:** `Demo12345!`

### 5. Fejlesztői szerver indítása

```bash
python manage.py runserver
```

- Alkalmazás: <http://127.0.0.1:8000/>
- Admin: <http://127.0.0.1:8000/admin/>

Adminisztrátori fiók létrehozása:

```bash
python manage.py createsuperuser
```

## PostgreSQL használata (éles/feltételes környezet)

A projekt alapértelmezésben SQLite-pal fut, de a beállítások és a modellek
teljes mértékben PostgreSQL-kompatibilisek. Váltás:

1. Telepítsd a PostgreSQL drivert:

   ```bash
   pip install "psycopg[binary]"
   ```

2. Hozz létre adatbázist és felhasználót (példa):

   ```sql
   CREATE USER homefinance WITH PASSWORD 'eros-jelszo';
   CREATE DATABASE homefinance OWNER homefinance;
   ```

3. Állítsd be a `.env` fájlban:

   ```env
   DATABASE_URL=postgres://homefinance:eros-jelszo@localhost:5432/homefinance
   ```

4. Futtasd a migrációkat:

   ```bash
   python manage.py migrate
   ```

A meglévő SQLite-adatok automatikusan nem kerülnek át PostgreSQL-be; szükség
esetén `dumpdata` / `loaddata` használható.

## Konfigurációs változók

| Változó | Leírás | Alapértelmezés |
| --- | --- | --- |
| `DEBUG` | Fejlesztői mód | `True` |
| `SECRET_KEY` | Django titkos kulcs | fejlesztői kulcs |
| `ALLOWED_HOSTS` | Engedélyezett hosztok, vesszővel | `localhost,127.0.0.1` |
| `DATABASE_URL` | Adatbázis URL | `sqlite:///<projekt>/db.sqlite3` |
| `DB_CONN_MAX_AGE` | Perzisztens DB kapcsolat másodpercben | `0` |
| `CSRF_TRUSTED_ORIGINS` | Megbízható origók élesben | üres |
| `SECURE_SSL_REDIRECT` | HTTPS kényszerítés (`DEBUG=False`) | `True` |
| `SESSION_COOKIE_SECURE` | Csak HTTPS-en küldje a session sütit | `True` |
| `CSRF_COOKIE_SECURE` | Csak HTTPS-en küldje a CSRF sütit | `True` |
| `LOG_LEVEL` | Naplózási szint | `INFO` |

Éles üzem előtt kötelező:

- Új `SECRET_KEY` generálása.
- `DEBUG=False`.
- `ALLOWED_HOSTS` és `CSRF_TRUSTED_ORIGINS` beállítása.
- HTTPS használata.
- `python manage.py collectstatic` futtatása, statikus kiszolgálás Nginx-szel
  vagy CDN-nel.

## Adatmodell

### User

- Egyedi, kisbetűsített **e-mail-cím** az azonosító (`USERNAME_FIELD = "email"`).
- Keresztnév, vezetéknév, aktív/admin/szuperfelhasználó jelzők.
- Jelszó csak hash formában tárolva (Django password hasher).
- Bejelentkezés e-mail-címmel, kis- és nagybetűtől függetlenül.

### Category

- `owner` – kötelező kapcsolat a felhasználóhoz (`CASCADE`).
- `name` – max. 100 karakter.
- `type` – `income` (bevétel) vagy `expense` (kiadás).
- Egy felhasználónál azonos név + típus nem ismételhető (adatbázis-szintű
  `UniqueConstraint`, valamint űrlapszintű, ékezetkezelő ellenőrzés).

### Transaction

- `owner` – kötelező felhasználói kapcsolat (`CASCADE`).
- `category` – kötelező kategória (`PROTECT`, használatban lévő kategória nem törölhető).
- `type` – a kategória típusával egyező `income` / `expense`.
- `amount` – pozitív, max. 2 tizedesjegy, max. 12 számjegy (`DecimalField`).
- `date` – tranzakció dátuma.
- `description` – opcionális leírás.
- Adatbázis-szintű `CHECK (amount > 0)` megszorítás.

## Üzleti szabályok és érvényesítésük

| Szabály | Hol valósul meg |
| --- | --- |
| Mindenki csak a saját adatait látja | `OwnerQuerysetMixin`, nézetek szűrése `owner=request.user` alapján |
| Pénznem HUF | Megjelenítés és űrlapok „Ft” jelöléssel; külön pénznemmező nincs |
| Összeg > 0, max. 2 tizedesjegy | `MinValueValidator`, `DecimalValidator`, `Transaction.clean()`, DB `CheckConstraint` |
| Tranzakció típusa = kategória típusa | `Transaction.clean()`, `TransactionForm.clean()`, űrlapmegjelenítés |
| Használatban lévő kategória nem törölhető | `on_delete=PROTECT` + nézetoldali ellenőrzés és magyar hibaüzenet |
| Használatban lévő kategória típusa nem módosítható | `Category.clean()` + űrlapvalidáció |
| Biztonságos jelszótárolás | Django `set_password` / password hashers |
| Jogosultságellenőrzés | `LoginRequiredMixin`, `@login_required`, owner-szűrt lekérdezések |
| Szerveroldali validáció | Django formok + model `clean`/`full_clean` + DB megszorítások |
| Törlés csak POST-tal | `@require_POST` + CSRF token |

## Tesztelés

```bash
# Teljes tesztcsomag
python manage.py test

# Gyorsabb, párhuzamos futtatás
python manage.py test --parallel 4
```

A tesztcsomag **94 tesztet** tartalmaz az alábbi területeken:

- **Modellek:** e-mail normalizálás/egyediség, szuperfelhasználó, kategória
  egyediség, összeg- és típusvalidáció, idegen kategória tiltása, `PROTECT`,
  sorrendezés.
- **Hitelesítés:** regisztráció, kis- és nagybetűtől független bejelentkezés,
  hibás jelszó, kijelentkezés (POST-only), védett oldalak átirányítása.
- **Tranzakciók:** létrehozás, módosítás, törlés, jogosultságok, adatelkülönítés,
  típus-/összegvalidáció, szűrések, lapozás, összesítések.
- **Kategóriák:** CRUD, duplikáció, ékezetkezelés, használatban lévő kategória
  törlésének tiltása, idegen adatok elérése.
- **Kimutatások:** havi összesítések, kategóriabontás, százalékok, trend,
  felhasználói adatelkülönítés, érvénytelen év/hónap kezelése.
- **Űrlapok:** összes validációs szabály és felhasználóhoz kötött választék.

## URL-ek

| Útvonal | Funkció |
| --- | --- |
| `/` | Vezérlőpult |
| `/tranzakciok/` | Tranzakciók listája, szűrés, keresés |
| `/tranzakciok/uj/` | Új tranzakció |
| `/tranzakciok/<id>/szerkesztes/` | Tranzakció szerkesztése |
| `/tranzakciok/<id>/torles/` | Tranzakció törlése (POST) |
| `/kategoriak/` | Kategóriák listája |
| `/kategoriak/uj/` | Új kategória |
| `/kategoriak/<id>/szerkesztes/` | Kategória szerkesztése |
| `/kategoriak/<id>/torles/` | Kategória törlése (POST) |
| `/kimutatasok/` | Havi kimutatások, grafikonok |
| `/regisztracio/` | Regisztráció |
| `/belepes/` | Bejelentkezés |
| `/kilepes/` | Kijelentkezés (POST) |
| `/admin/` | Django adminisztráció |

## Fejlesztési döntések

1. **SQLite fejlesztéshez, PostgreSQL éleshez.** A rendelkezésre álló környezetben
   nem volt PostgreSQL és nem volt `sudo` a telepítéshez. Ezért a projekt
   `django-environ` segítségével konfigurálható: alapból SQLite-pal fut, de a
   `DATABASE_URL` megadásával migrációk nélkül váltható PostgreSQL-re. A modellek
   és a migrációk PostgreSQL-kompatibilisek.
2. **Egyedi User modell.** Az e-mail-cím az elsődleges bejelentkezési azonosító,
   a felhasználói nevet nem használjuk külön mezőként.
3. **A tranzakció típusa redundánsan tárolt.** A követelmény kifejezetten kéri,
   hogy a tranzakció típusa egyezzen a kategóriáéval; ezt model- és
   űrlapszinten is ellenőrizzük, így a lista szűrése gyors és egyértelmű.
4. **Kategória törlése `PROTECT`-tel.** Így adatbázis-szinten sem veszhet el
   tranzakció, a nézet pedig barátságos magyar hibaüzenetet ad.
5. **Magyar összegformázás.** Egyedi `huf` szűrő: ezres tagolás nem törhető
   szóközzel, tizedesvesszővel (pl. `1 234 567 Ft`, `1 234,50 Ft`).
6. **Bootstrap és Chart.js CDN-ről.** Kevesebb saját kód, gyorsabb fejlesztés.
   Internet hiányában a grafikonok helyett szöveges tartalék jelenik meg, a
   többi funkció változatlanul működik.
7. **Chart.js adatok `json_script`-ben.** Biztonságos JSON-átadás a sablonból,
   nincs inline szkript-összefűzés.
8. **Nincs felesleges technológia.** Nincs REST API, Docker, Redis, Celery vagy
   külön frontend keretrendszer, mert a feladat ezeket nem igényli.

## Biztonsági megjegyzések

- Minden módosító művelet CSRF-védelemmel és POST-metódussal működik.
- A jelszavakat a Django biztonságos hash-eléssel tárolja.
- Az objektumok lekérdezése minden nézetben `owner=request.user` szűréssel
  történik, így más felhasználó adatai nem érhetők el (404).
- Az űrlapok és a modellek szerveroldalon is validálnak; a kliensoldali
  `required` mezők csak kényelmi funkciók.
- `DEBUG=False` esetén a beállítások HTTPS-t, secure sütiket és
  `X-Frame-Options: DENY` fejlécet kapcsolnak.
- Éles üzem előtt cseréld le a `SECRET_KEY` értékét, és ne commitold a `.env` fájlt.

## A rendszer nem tartalmazza (a követelmény szerint)

- Banki API-kapcsolatot vagy automatikus banki importot.
- Közös, többfelhasználós pénztárcát.
- Több pénznem kezelését.
- Befektetéskezelési funkciókat.

## Ismert korlátok és lehetséges következő lépések

- Nincs e-mail-visszaigazolás, elfelejtett jelszó és kétfaktoros hitelesítés
  (a követelmény nem írta elő).
- Nincs ismétlődő (recurring) tranzakció.
- A felület stílusához és grafikonjaihoz internetkapcsolat kell a CDN miatt.
- Éles környezethez érdemes Gunicorn + Nginx kombinációt, külön statikus
  kiszolgálást és rendszeres adatbázis-mentést beállítani.
- Nagy adatmennyiségnél a kimutatások további indexeléssel vagy gyorsítótárral
  optimalizálhatók.

## Gyors ellenőrzőlista

```bash
python manage.py check           # konfiguráció ellenőrzése
python manage.py migrate         # adatbázis létrehozása
python manage.py seed_demo       # opcionális demó adatok
python manage.py test            # tesztek futtatása
python manage.py runserver       # indítás
```
