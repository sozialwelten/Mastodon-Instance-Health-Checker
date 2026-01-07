#!/usr/bin/env python3
"""
Mastodon-Instance-Health-Checker
Prüft technische Gesundheit und Performance von Mastodon-Instanzen
"""

import requests
import argparse
import sys
import time
import json
import csv
from datetime import datetime
from urllib.parse import urlparse


class InstanceHealthChecker:
    def __init__(self, instance):
        """
        instance: Mastodon-Instanz (z.B. 'mastodon.social')
        """
        self.instance = instance.replace('https://', '').replace('http://', '').strip('/')
        self.base_url = f"https://{self.instance}"
        self.health_data = {}

    def check_reachability(self):
        """Prüft grundlegende Erreichbarkeit"""
        try:
            start = time.time()
            response = requests.get(self.base_url, timeout=10)
            latency = int((time.time() - start) * 1000)

            return {
                'status': 'ok' if response.status_code == 200 else 'warning',
                'latency_ms': latency,
                'status_code': response.status_code,
                'https': response.url.startswith('https://')
            }
        except requests.exceptions.SSLError:
            return {'status': 'error', 'message': 'SSL-Fehler'}
        except requests.exceptions.Timeout:
            return {'status': 'error', 'message': 'Timeout'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def check_api(self):
        """Prüft API-Verfügbarkeit"""
        try:
            # Prüfe API v2 Instance Endpoint
            response = requests.get(
                f"{self.base_url}/api/v2/instance",
                timeout=10
            )

            if response.status_code == 200:
                return {
                    'status': 'ok',
                    'version': 'v2',
                    'data': response.json()
                }

            # Fallback: API v1
            response = requests.get(
                f"{self.base_url}/api/v1/instance",
                timeout=10
            )

            if response.status_code == 200:
                return {
                    'status': 'ok',
                    'version': 'v1',
                    'data': response.json()
                }

            return {'status': 'error', 'message': f'Status {response.status_code}'}

        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def check_nodeinfo(self):
        """Prüft NodeInfo (Federation-Standard)"""
        try:
            # Hole NodeInfo-URL via Well-Known
            response = requests.get(
                f"{self.base_url}/.well-known/nodeinfo",
                timeout=10
            )

            if response.status_code != 200:
                return {'status': 'warning', 'message': 'NodeInfo nicht verfügbar'}

            nodeinfo_data = response.json()
            nodeinfo_url = None

            # Finde aktuellste NodeInfo-Version
            for link in nodeinfo_data.get('links', []):
                if 'nodeinfo/2.' in link.get('href', ''):
                    nodeinfo_url = link['href']
                    break

            if not nodeinfo_url:
                return {'status': 'warning', 'message': 'NodeInfo-Link nicht gefunden'}

            # Hole NodeInfo
            response = requests.get(nodeinfo_url, timeout=10)
            if response.status_code == 200:
                return {
                    'status': 'ok',
                    'data': response.json()
                }

            return {'status': 'warning', 'message': 'NodeInfo nicht erreichbar'}

        except Exception as e:
            return {'status': 'warning', 'message': str(e)}

    def check_timeline_performance(self):
        """Prüft Timeline-Performance"""
        try:
            start = time.time()
            response = requests.get(
                f"{self.base_url}/api/v1/timelines/public",
                params={'limit': 20, 'local': True},
                timeout=15
            )
            latency = int((time.time() - start) * 1000)

            if response.status_code == 200:
                posts = response.json()
                return {
                    'status': 'ok',
                    'latency_ms': latency,
                    'posts_count': len(posts)
                }

            return {'status': 'warning', 'message': f'Status {response.status_code}'}

        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def check_streaming(self):
        """Prüft Streaming-API"""
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/streaming/health",
                timeout=10
            )

            return {
                'status': 'ok' if response.status_code == 200 else 'warning',
                'available': response.status_code == 200
            }

        except Exception as e:
            return {'status': 'warning', 'message': 'Nicht erreichbar'}

    def check_media_upload(self):
        """Prüft ob Media-Upload funktioniert (ohne wirklich hochzuladen)"""
        try:
            # Prüfe nur ob Endpoint antwortet (403/401 = funktioniert, benötigt Auth)
            response = requests.post(
                f"{self.base_url}/api/v2/media",
                timeout=10
            )

            # 401/403 bedeutet: Endpoint existiert, braucht nur Auth
            if response.status_code in [401, 403]:
                return {'status': 'ok', 'available': True}

            return {'status': 'warning', 'message': f'Unerwarteter Status {response.status_code}'}

        except Exception as e:
            return {'status': 'warning', 'message': str(e)}

    def check_security_headers(self):
        """Prüft Security-Header"""
        try:
            response = requests.get(self.base_url, timeout=10)
            headers = response.headers

            checks = {
                'https': response.url.startswith('https://'),
                'hsts': 'Strict-Transport-Security' in headers,
                'csp': 'Content-Security-Policy' in headers,
                'x_frame_options': 'X-Frame-Options' in headers,
                'x_content_type_options': 'X-Content-Type-Options' in headers
            }

            score = sum(checks.values())

            return {
                'status': 'ok' if score >= 4 else 'warning',
                'checks': checks,
                'score': score,
                'max_score': len(checks)
            }

        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def check_rate_limiting(self):
        """Prüft ob Rate-Limiting aktiv ist"""
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/timelines/public",
                timeout=10
            )

            has_rate_limit = any(
                header.startswith('X-RateLimit')
                for header in response.headers
            )

            return {
                'status': 'ok' if has_rate_limit else 'warning',
                'active': has_rate_limit,
                'headers': {
                    k: v for k, v in response.headers.items()
                    if k.startswith('X-RateLimit')
                }
            }

        except Exception as e:
            return {'status': 'warning', 'message': str(e)}

    def run_full_check(self):
        """Führt alle Checks aus"""
        print(f"🏥 Health Check: {self.instance}\n")

        # Erreichbarkeit
        print("Prüfe Erreichbarkeit...", end=' ')
        reachability = self.check_reachability()
        self.health_data['reachability'] = reachability

        if reachability['status'] == 'error':
            print(f"❌ {reachability.get('message', 'Fehler')}")
            print(f"\n❌ Instanz nicht erreichbar!\n")
            return False

        print(f"✅ OK ({reachability['latency_ms']}ms)")

        # API
        print("Prüfe API...", end=' ')
        api = self.check_api()
        self.health_data['api'] = api

        if api['status'] == 'ok':
            print(f"✅ {api['version'].upper()}")
        else:
            print(f"❌ {api.get('message', 'Fehler')}")

        # NodeInfo
        print("Prüfe Federation...", end=' ')
        nodeinfo = self.check_nodeinfo()
        self.health_data['nodeinfo'] = nodeinfo
        print("✅ Aktiv" if nodeinfo['status'] == 'ok' else f"⚠️  {nodeinfo.get('message', 'Fehler')}")

        # Timeline Performance
        print("Prüfe Timeline-Performance...", end=' ')
        timeline = self.check_timeline_performance()
        self.health_data['timeline'] = timeline

        if timeline['status'] == 'ok':
            print(f"✅ {timeline['latency_ms']}ms")
        else:
            print(f"⚠️  {timeline.get('message', 'Fehler')}")

        # Streaming
        print("Prüfe Streaming-API...", end=' ')
        streaming = self.check_streaming()
        self.health_data['streaming'] = streaming
        print("✅ Aktiv" if streaming['status'] == 'ok' else "⚠️  Inaktiv")

        # Media Upload
        print("Prüfe Media-Upload...", end=' ')
        media = self.check_media_upload()
        self.health_data['media'] = media
        print("✅ Verfügbar" if media['status'] == 'ok' else "⚠️  Problem")

        # Security Headers
        print("Prüfe Security-Headers...", end=' ')
        security = self.check_security_headers()
        self.health_data['security'] = security

        if security['status'] == 'ok':
            print(f"✅ {security['score']}/{security['max_score']}")
        else:
            print(f"⚠️  {security['score']}/{security['max_score']}")

        # Rate Limiting
        print("Prüfe Rate-Limiting...", end=' ')
        rate_limit = self.check_rate_limiting()
        self.health_data['rate_limiting'] = rate_limit
        print("✅ Aktiv" if rate_limit['status'] == 'ok' else "⚠️  Inaktiv")

        print()
        return True

    def print_detailed_report(self):
        """Gibt detaillierten Report aus"""
        print("=" * 80)

        # Instanz-Infos
        if self.health_data.get('api', {}).get('status') == 'ok':
            data = self.health_data['api']['data']

            print("\n📊 Instanz-Informationen:")
            print(f"   Titel: {data.get('title', 'N/A')}")
            print(f"   Version: {data.get('version', 'N/A')}")
            print(f"   Beschreibung: {data.get('description', 'N/A')[:100]}...")

            # Stats (je nach API-Version unterschiedlich)
            if 'usage' in data:
                usage = data['usage'].get('users', {})
                print(f"\n   Nutzer (aktiv): {usage.get('active_month', 'N/A')}")
            elif 'stats' in data:
                stats = data['stats']
                print(f"\n   Nutzer: {stats.get('user_count', 'N/A'):,}")
                print(f"   Posts: {stats.get('status_count', 'N/A'):,}")
                print(f"   Föderierte Instanzen: {stats.get('domain_count', 'N/A'):,}")

            # Registrierung
            if 'registrations' in data:
                reg = data['registrations']
                reg_status = "Offen" if reg.get('enabled') else "Geschlossen"
                approval = " (Freigabe erforderlich)" if reg.get('approval_required') else ""
                print(f"\n   Registrierung: {reg_status}{approval}")

            # Konfiguration
            if 'configuration' in data:
                config = data['configuration']
                if 'statuses' in config:
                    print(f"\n   Max. Zeichen/Post: {config['statuses'].get('max_characters', 'N/A')}")
                if 'media_attachments' in config:
                    media_config = config['media_attachments']
                    print(f"   Max. Medien-Uploads: {media_config.get('supported_mime_types', []).__len__()} Formate")

        # NodeInfo
        if self.health_data.get('nodeinfo', {}).get('status') == 'ok':
            nodeinfo = self.health_data['nodeinfo']['data']
            software = nodeinfo.get('software', {})

            print(f"\n💻 Software:")
            print(f"   Name: {software.get('name', 'N/A')}")
            print(f"   Version: {software.get('version', 'N/A')}")

            if 'metadata' in nodeinfo:
                metadata = nodeinfo['metadata']
                if 'nodeName' in metadata:
                    print(f"   Node-Name: {metadata['nodeName']}")

        # Performance
        print("\n⚡ Performance:")

        if 'reachability' in self.health_data:
            print(f"   Basis-Latenz: {self.health_data['reachability'].get('latency_ms', 'N/A')}ms")

        if self.health_data.get('timeline', {}).get('status') == 'ok':
            print(f"   Timeline-Latenz: {self.health_data['timeline']['latency_ms']}ms")

        # Sicherheit
        if self.health_data.get('security', {}).get('status') in ['ok', 'warning']:
            security = self.health_data['security']
            checks = security['checks']

            print("\n🔒 Sicherheit:")
            print(f"   HTTPS: {'✅' if checks.get('https') else '❌'}")
            print(f"   HSTS: {'✅' if checks.get('hsts') else '❌'}")
            print(f"   Content-Security-Policy: {'✅' if checks.get('csp') else '❌'}")
            print(f"   X-Frame-Options: {'✅' if checks.get('x_frame_options') else '❌'}")
            print(f"   X-Content-Type-Options: {'✅' if checks.get('x_content_type_options') else '❌'}")

        # Gesamt-Score
        score = self.calculate_health_score()
        print(f"\n💚 Gesamt-Score: {score}/100", end=' ')

        if score >= 90:
            print("(Ausgezeichnet)")
        elif score >= 75:
            print("(Sehr gut)")
        elif score >= 60:
            print("(Gut)")
        elif score >= 40:
            print("(Befriedigend)")
        else:
            print("(Probleme festgestellt)")

        print("\n" + "=" * 80 + "\n")

    def calculate_health_score(self):
        """Berechnet Gesamt-Health-Score (0-100)"""
        score = 0

        # Erreichbarkeit (20 Punkte)
        if self.health_data.get('reachability', {}).get('status') == 'ok':
            score += 20
            latency = self.health_data['reachability'].get('latency_ms', 1000)
            if latency < 200:
                score += 5
            elif latency < 500:
                score += 3

        # API (15 Punkte)
        if self.health_data.get('api', {}).get('status') == 'ok':
            score += 15

        # Federation (10 Punkte)
        if self.health_data.get('nodeinfo', {}).get('status') == 'ok':
            score += 10

        # Timeline Performance (15 Punkte)
        if self.health_data.get('timeline', {}).get('status') == 'ok':
            score += 10
            latency = self.health_data['timeline'].get('latency_ms', 1000)
            if latency < 300:
                score += 5
            elif latency < 600:
                score += 3

        # Streaming (10 Punkte)
        if self.health_data.get('streaming', {}).get('status') == 'ok':
            score += 10

        # Media Upload (10 Punkte)
        if self.health_data.get('media', {}).get('status') == 'ok':
            score += 10

        # Security (15 Punkte)
        if self.health_data.get('security', {}).get('status') in ['ok', 'warning']:
            sec_score = self.health_data['security']['score']
            sec_max = self.health_data['security']['max_score']
            score += int(15 * (sec_score / sec_max))

        # Rate Limiting (5 Punkte)
        if self.health_data.get('rate_limiting', {}).get('status') == 'ok':
            score += 5

        return min(score, 100)

    def export_csv(self, filename):
        """Exportiert Ergebnisse als CSV"""
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Instance', 'Score', 'Reachable', 'API', 'Federation', 'Latency_ms', 'Security_Score'])

            writer.writerow([
                self.instance,
                self.calculate_health_score(),
                self.health_data.get('reachability', {}).get('status') == 'ok',
                self.health_data.get('api', {}).get('status') == 'ok',
                self.health_data.get('nodeinfo', {}).get('status') == 'ok',
                self.health_data.get('reachability', {}).get('latency_ms', 'N/A'),
                self.health_data.get('security', {}).get('score', 'N/A')
            ])

        print(f"💾 Exportiert nach: {filename}\n")


def compare_instances(instances):
    """Vergleicht mehrere Instanzen"""
    print("\n" + "=" * 80)
    print("📊 Instanz-Vergleich")
    print("=" * 80 + "\n")

    results = []

    for instance in instances:
        checker = InstanceHealthChecker(instance)
        print(f"Prüfe {instance}...")
        if checker.run_full_check():
            results.append({
                'instance': instance,
                'score': checker.calculate_health_score(),
                'data': checker.health_data
            })
        print()

    # Sortiere nach Score
    results.sort(key=lambda x: x['score'], reverse=True)

    print("=" * 80)
    print("\n🏆 Ranking:\n")

    for i, result in enumerate(results, 1):
        score = result['score']
        instance = result['instance']

        latency = result['data'].get('reachability', {}).get('latency_ms', 'N/A')
        api_ok = '✅' if result['data'].get('api', {}).get('status') == 'ok' else '❌'

        print(f"   {i}. {instance}")
        print(f"      Score: {score}/100 | Latenz: {latency}ms | API: {api_ok}")
        print()

    print("=" * 80 + "\n")


def monitor_instance(instance, interval):
    """Monitoring-Modus"""
    print(f"🔄 Monitoring-Modus für {instance} (alle {interval}s)")
    print("   Drücke Ctrl+C zum Beenden\n")

    try:
        while True:
            checker = InstanceHealthChecker(instance)
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            print(f"[{timestamp}]")
            if checker.run_full_check():
                score = checker.calculate_health_score()
                print(f"   💚 Score: {score}/100\n")
            else:
                print("   ❌ Check fehlgeschlagen\n")

            time.sleep(interval)

    except KeyboardInterrupt:
        print("\n\n✋ Monitoring beendet\n")


def main():
    parser = argparse.ArgumentParser(
        description='Mastodon-Instance-Health-Checker: Prüfe technische Gesundheit von Instanzen',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Beispiele:
  %(prog)s mastodon.social
  %(prog)s chaos.social --export health.csv
  %(prog)s mastodon.social chaos.social fosstodon.org --compare
  %(prog)s mastodon.social --monitor --interval 300
        """
    )

    parser.add_argument('instances', nargs='+',
                        help='Mastodon-Instanz(en) (z.B. mastodon.social)')
    parser.add_argument('--compare', action='store_true',
                        help='Vergleiche mehrere Instanzen')
    parser.add_argument('--export',
                        help='Exportiere als CSV')
    parser.add_argument('--monitor', action='store_true',
                        help='Monitoring-Modus (kontinuierlich prüfen)')
    parser.add_argument('--interval', type=int, default=300,
                        help='Monitoring-Intervall in Sekunden (Standard: 300)')

    args = parser.parse_args()

    # Banner
    print("\n" + "=" * 80)
    print("🏥 Mastodon-Instance-Health-Checker")
    print("   Technische Gesundheit und Performance-Analyse")
    print("=" * 80 + "\n")

    # Monitoring-Modus (nur für eine Instanz)
    if args.monitor:
        if len(args.instances) > 1:
            print("❌ Monitoring-Modus funktioniert nur mit einer Instanz\n")
            sys.exit(1)

        monitor_instance(args.instances[0], args.interval)
        return

    # Vergleichs-Modus
    if args.compare or len(args.instances) > 1:
        compare_instances(args.instances)
        return

    # Single-Instance Check
    checker = InstanceHealthChecker(args.instances[0])

    if checker.run_full_check():
        checker.print_detailed_report()

        if args.export:
            checker.export_csv(args.export)


if __name__ == "__main__":
    main()