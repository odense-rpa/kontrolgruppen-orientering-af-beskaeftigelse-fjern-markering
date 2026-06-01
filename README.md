## Kontrolgruppen – Orientering af beskæftigelse – Fjern markering

Automatisering der fjerner markeringen _"Igangværende kontrolgruppe sag"_ i Momentum, når en borger ikke længere har aktive kontrolsager i SBSYS.

## Hvad gør robotten?

1. **Finder borgere med aktiv markering** – henter alle borgere i Momentum med markeringen _"Igangværende kontrolgruppe sag"_
2. **Fylder arbejdskøen** med borgernes CPR-numre
3. **Tjekker SBSYS** – for hver borger søges der efter aktive sager (status 6) på tværs af de relevante kontrolgruppeskabeloner:
   - Adresse – Kontrolgruppen
   - Kontrolsager fra Udbetaling Danmark – Kontrolgruppen
   - Samliv – Kontrolgruppen
   - Sort arbejde – Kontrolgruppen
   - Udrejse – Kontrolgruppen
   - Øvrige kontrolsager – Kontrolgruppen
4. **Afslutter markeringen** i Momentum hvis borgeren ikke har nogen aktive kontrolsager i SBSYS

## Forudsætninger

- Python ≥ 3.13
- [`uv`](https://docs.astral.sh/uv/) til pakkehåndtering
- Adgang til **Automation Server** (arbejdskø)
- Adgang til **SBSYS** (produktion)
- Adgang til **Momentum** (produktion)
- En **Odense SQL Server**-konto til aktivitetssporing

## Installation

```sh
uv sync
```

## Konfiguration

Alle legitimationsoplysninger hentes via Automation Server Credentials — ingen oplysninger må hardkodes eller placeres i kode:

| Credential-navn           | Beskrivelse                        |
|---------------------------|------------------------------------|
| `Odense SQL Server`       | Aktivitetssporing (tracking)       |
| `Momentum - produktion`   | Momentum API (borgere og markeringer) |
| `SBSYS - produktion`      | SBSYS API (sagssøgning)            |

## Kørsel

```sh
# Fyld arbejdskøen med borgere der har aktiv markering i Momentum
uv run python main.py --queue

# Behandl arbejdskøen og fjern markeringer for borgere uden aktive sager
uv run python main.py
```

## Afhængigheder

| Pakke                       | Formål                        |
|-----------------------------|-------------------------------|
| `automation-server-client`  | Arbejdskø-håndtering          |
| `sbsys`                     | Integration med SBSYS         |
| `momentum-client`           | Integration med Momentum      |
| `odk-tools`                 | Aktivitetssporing             |

## Persondatasikkerhed

Robotten behandler personoplysninger på vegne af Odense Kommune, herunder CPR-numre i forbindelse med kontrolsager (jf. databeskyttelsesloven § 11 og GDPR art. 10 om behandling af oplysninger vedrørende lovovertrædelser).

- **Ingen personoplysninger** må lægges i dette repository — hverken som testdata, i kode eller i kommentarer
- **CPR-numre logges aldrig** — fejlbeskeder er generiske og indeholder ikke borgerdata
- **Legitimationsoplysninger** håndteres udelukkende via Automation Server Credentials og må aldrig hardkodes
- `input/`-mappen og `.env`-filen er ekskluderet via `.gitignore` og må aldrig committes
