import json
import time
import random
import sys
import socket
from datetime import datetime, timezone

# Konfiguracja danych symulacyjnych
FACULTIES = [
    "Wydział Matematyki i Informatyki",
    "Wydział Prawa i Administracji",
    "Wydział Filozoficzny",
    "Wydział Zarządzania i Komunikacji Społecznej",
    "Wydział Fizyki, Astronomii i Informatyki Stosowanej",
    "Wydział Lekarski"
]

ACTIONS_NORMAL = ["login", "view_courses", "view_grades", "logout"]
ACTIONS_CRASH = ["register_attempt", "register_attempt", "register_attempt", "refresh_page"]

ENDPOINTS = {
    "login": "/api/usos/auth/login",
    "logout": "/api/usos/auth/logout",
    "view_courses": "/api/usos/courses/list",
    "view_grades": "/api/usos/grades",
    "register_attempt": "/api/usos/registration/submit",
    "refresh_page": "/api/usos/registration/status"
}

# NOWE
FILEBEAT_HOST = "filebeat" # Nazwa kontenera w sieci Docker
FILEBEAT_PORT = 9000

# NOWE
def connect_to_filebeat():
    """Próbuje połączyć się z Filebeatem aż do skutku"""
    while True:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((FILEBEAT_HOST, FILEBEAT_PORT))
            print("Połączono z Filebeat przez TCP!", file=sys.stderr)
            return sock
        except Exception as e:
            print(f"Czekam na Filebeata (Port {FILEBEAT_PORT})...", file=sys.stderr)
            time.sleep(3)

def generate_ip_and_location():
    if random.random() < 0.80:
        lat = 50.0614 + random.uniform(-0.05, 0.05)
        lon = 19.9365 + random.uniform(-0.05, 0.05)
        ip = f"149.156.{random.randint(1, 255)}.{random.randint(1, 255)}"
    else:
        lat = random.uniform(40.0, 60.0)
        lon = random.uniform(-10.0, 30.0)
        ip = f"{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}"
    return ip, {"lat": round(lat, 5), "lon": round(lon, 5)}

def generate_log_event(is_crash_mode):
    action = random.choice(ACTIONS_CRASH) if is_crash_mode else random.choice(ACTIONS_NORMAL)
    endpoint = ENDPOINTS[action]
    
    if is_crash_mode:
        status_code = random.choices([200, 429, 500, 502, 504], weights=[10, 30, 40, 10, 10])[0]
        response_time = random.randint(5000, 30000) if status_code != 429 else random.randint(10, 50)
    else:
        status_code = random.choices([200, 400, 401, 500], weights=[95, 2, 2, 1])[0]
        response_time = random.randint(20, 300)

    ip, location = generate_ip_and_location()

    # NOWE
    log_entry = {
        "@timestamp": datetime.now(timezone.utc).isoformat(),
        "student_id": f"{random.randint(1000000, 1099999)}",
        "faculty": random.choice(FACULTIES),
        "action": action,
        "endpoint": endpoint,
        "status_code": status_code,
        "response_time_ms": response_time,
        "client_ip": ip,
        "location": location,
        "transport": "network",
        "dupa": "z sieci"
    }
    return log_entry

def main():
    print("Rozpoczęto generowanie logów (Wersja SIECIOWA)...", file=sys.stderr)
    sock = connect_to_filebeat()
    
    normal_duration = 60  
    crash_duration = 30   
    
    while True:
        try:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Tryb NORMALNY (Sieć)", file=sys.stderr)
            end_time = time.time() + normal_duration
            while time.time() < end_time:
                log = generate_log_event(is_crash_mode=False)
                # Wysyłamy log jako ciąg bajtów zakończony znakiem nowej linii
                sock.sendall((json.dumps(log) + '\n').encode('utf-8'))
                time.sleep(random.uniform(0.3, 1.0))
                
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Tryb AWARII (Sieć)", file=sys.stderr)
            end_time = time.time() + crash_duration
            while time.time() < end_time:
                log = generate_log_event(is_crash_mode=True)
                sock.sendall((json.dumps(log) + '\n').encode('utf-8'))
                time.sleep(random.uniform(0.03, 0.08))
                
        except (BrokenPipeError, ConnectionResetError):
            # Jeśli Filebeat z jakiegoś powodu zerwie połączenie, łączymy się ponownie
            print("Połączenie zerwane. Próbuję połączyć ponownie...", file=sys.stderr)
            sock.close()
            sock = connect_to_filebeat()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)