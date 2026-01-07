# Mastodon-Instance-Health-Checker

Prüft technische Gesundheit und Performance von Mastodon-Instanzen. Ideal zur Evaluierung vor einer Migration oder zum Monitoring der eigenen Instanz.

## Features

- 🏥 Umfassende Health-Checks (Erreichbarkeit, API, Federation)
- ⚡ Performance-Messungen (Latenz, Response-Zeiten)
- 🔒 Sicherheits-Analyse (HTTPS, Security-Headers, Rate-Limiting)
- 📊 Detaillierte Instanz-Informationen
- 🏆 Instanz-Vergleich mit Ranking
- 🔄 Monitoring-Modus für kontinuierliche Überwachung
- 💾 CSV-Export
- 💚 Scoring-System (0-100 Punkte)

## Installation

```bash
pip install requests
```

## Verwendung

```bash
# Einzelne Instanz prüfen
python instance_health.py mastodon.social

# Mehrere Instanzen vergleichen
python instance_health.py mastodon.social chaos.social fosstodon.org

# Mit CSV-Export
python instance_health.py mastodon.social --export health.csv

# Monitoring-Modus (prüft alle 5 Minuten)
python instance_health.py mastodon.social --monitor --interval 300
```

## Optionen

```
positional arguments:
  instances            Mastodon-Instanz(en) (z.B. mastodon.social)

optional arguments:
  -h, --help          Hilfe anzeigen
  --compare           Vergleiche mehrere Instanzen
  --export FILE       Exportiere als CSV
  --monitor           Monitoring-Modus (kontinuierlich prüfen)
  --interval N        Monitoring-Intervall in Sekunden (Standard: 300)
```

## Beispiel-Output

```
🏥 Health Check: mastodon.social

Prüfe Erreichbarkeit... ✅ OK (124ms)
Prüfe API... ✅ V2
Prüfe Federation... ✅ Aktiv
Prüfe Timeline-Performance... ✅ 234ms
Prüfe Streaming-API... ✅ Aktiv
Prüfe Media-Upload... ✅ Verfügbar
Prüfe Security-Headers... ✅ 5/5
Prüfe Rate-Limiting... ✅ Aktiv

================================================================================

📊 Instanz-Informationen:
   Titel: Mastodon
   Version: 4.2.1
   Nutzer (aktiv): 89.234

⚡ Performance:
   Basis-Latenz: 124ms
   Timeline-Latenz: 234ms

🔒 Sicherheit:
   HTTPS: ✅
   HSTS: ✅
   Content-Security-Policy: ✅
   X-Frame-Options: ✅
   X-Content-Type-Options: ✅

💚 Gesamt-Score: 94/100 (Ausgezeichnet)
```

## Use Cases

- **Vor Migration**: Welche Instanz ist am stabilsten?
- **Admin-Tool**: Monitoring der eigenen Instanz
- **Community**: Fact-basierte Instanz-Empfehlungen
- **Debugging**: Schnelle Diagnose von Instanz-Problemen

## Lizenz

GPL-3.0

## Autor

Michael Karbacher