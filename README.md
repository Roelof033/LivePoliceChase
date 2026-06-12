# Police Chase Monitor

Gratis monitor die elke 30 minuten via GitHub Actions zoekt naar live
police chase streams op YouTube en een pushmelding stuurt via ntfy.sh.

## Setup (eenmalig, ~5 minuten)

1. **Maak een nieuwe GitHub-repository** (privé mag) en upload de inhoud
   van deze map: `chase_monitor.py` en de map `.github/workflows/`.

2. **Voeg je geheimen toe** in de repo:
   ga naar *Settings → Secrets and variables → Actions → New repository secret*
   en maak twee secrets aan:
   - `YOUTUBE_API_KEY` — je YouTube Data API v3 key
   - `NTFY_TOPIC` — je ntfy-topic (bijv. `chase-alerts-x7k2-geheim`)

3. **Telefoon**: installeer de ntfy-app en abonneer je op hetzelfde topic.

4. **Testen**: ga naar de *Actions*-tab → "Police Chase Monitor" →
   *Run workflow*. In de logs zie je wat er gebeurt.

Daarna draait alles vanzelf, elke 30 minuten — ook als je pc uitstaat.

## Goed om te weten

- **Kosten**: niets. Een privérepo heeft 2.000 gratis Actions-minuten per
  maand; deze workflow gebruikt er hooguit ~1.000. Bij een publieke repo
  zijn de minuten zelfs onbeperkt — maar zet je API-key dan zeker NIET in
  de code, alleen in Secrets (dat doet deze setup al).
- **Vertraging**: GitHub kan geplande runs op drukke momenten een paar
  minuten tot soms langer uitstellen. Voor dit doel is dat prima.
- **Inactiviteit**: GitHub pauzeert geplande workflows na ~60 dagen zonder
  activiteit in de repo. Je krijgt dan een mailtje; één klik op
  "re-enable" en hij draait weer.
- **seen.json**: dit bestand onthoudt welke streams al gemeld zijn, zodat
  je geen dubbele alerts krijgt. De workflow commit het zelf terug.
- **Quotum**: 2 zoektermen x 48 runs/dag = 9.600 quota-eenheden, net
  binnen de gratis 10.000/dag van de YouTube API. Voeg dus geen extra
  zoektermen toe zonder het cron-interval te verruimen.
"# LivePoliceChase" 
