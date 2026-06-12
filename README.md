# Police Chase Monitor v2

Checkt elke 5 minuten of bekende chase-kanalen (KTLA, FOX 11 LA, LiveNOW
from FOX, ...) live een pursuit uitzenden, plus 1x per uur een brede
YouTube-zoektocht als vangnet. Pushmeldingen via ntfy.sh.

## Updaten vanaf v1
Vervang `chase_monitor.py` en `.github/workflows/monitor.yml` in je repo
door de nieuwe versies. Secrets blijven hetzelfde.

## BELANGRIJK: maak je repo publiek (of verlaag de frequentie)
Elke 5 minuten = ~288 runs per dag. Een privérepo heeft maar 2.000 gratis
Actions-minuten per maand en elke run telt als minimaal 1 minuut — dat
red je niet. Een publieke repo heeft ONBEPERKTE gratis minuten.
Je secrets (API-key, ntfy-topic) blijven ook in een publieke repo
gewoon geheim; alleen de code en seen.json zijn zichtbaar.
Wil je toch privé blijven: zet de cron op "*/20 * * * *" of ruimer.

## Hoe het filtert
- Alert alleen bij titels met "chase", "pursuit" of "standoff"
- Blacklist blokkeert gaming/roleplay/compilatie-rommel (gta, fivem,
  compilation, best of, ...) — uit te breiden bovenin het script
- Kanalen toevoegen aan WATCHLIST kost niets: de live-check gebruikt
  geen API-quotum

## Kanttekening
De watchlist-check leest de openbare /live-pagina van YouTube uit
(onofficieel). Als YouTube zijn pagina's verandert kan die check breken;
de uurlijkse API-zoektocht blijft dan als vangnet werken.
