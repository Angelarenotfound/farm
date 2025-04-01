from colorama import init, Fore, Back, Style
from threading import Thread
from time import sleep
import datetime
import requests
import json
from flask import Flask, jsonify

app = Flask(__name__)

# Inicializar Colorama
init()

class User:
    def __init__(self, apikey, color):
        self.apikey = apikey
        self.color = f'\033[{color}'
        self._running = False
        self._headers = {
            "Authorization": f"Bearer {apikey}",
            "Content-Type": "application/json",
            "Accept": "Application/vnd.pterodactyl.v1+json"
        }
        self._baseURL = "https://panel.sillydev.co.uk/api/"
        
        # Verificar token al iniciar
        r = requests.get(self._baseURL + "client/account", headers=self._headers)
        if r.status_code != 200:
            raise Exception("Token inválido")
        self.userdata = r.json()["attributes"]
        self.last_balance = 0
        self.last_error = None

    def _log(self, text):
        time = datetime.datetime.now().strftime("%H:%M:%S %d/%m")
        print(f"{self.color}{self.userdata['username']}{Style.RESET_ALL} [{time}] {text}")

    def get_balance(self):
        r = requests.get(self._baseURL + "client/store", headers=self._headers)
        if r.status_code == 200:
            self.last_balance = r.json()["attributes"]["balance"]
            return self.last_balance
        else:
            self.last_error = f"Error al obtener balance: HTTP {r.status_code}"
            return None

    def main_loop(self):
        while self._running:
            try:
                sleep(60)  # Esperar 60 segundos entre ejecuciones
                r = requests.post(self._baseURL + "client/store/earn", headers=self._headers)
                if r.status_code == 204:
                    balance = self.get_balance()
                    self._log(f"Créditos reclamados | Balance: {balance}$")
                elif r.status_code == 429:
                    self._log("Rate limit alcanzado, esperando 60 segundos...")
                    sleep(60)
            except Exception as e:
                self.last_error = str(e)
                self._log(f"Error: {e}")

    def start(self):
        self._running = True
        self.thread = Thread(target=self.main_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self._running = False
        self.thread.join()

# Cargar usuarios desde users.json
try:
    with open('users.json', 'r') as f:
        users = json.load(f)
except Exception as e:
    print(f"Error cargando users.json: {e}")
    users = {}

# Iniciar todos los usuarios
active_users = []
for username, config in users.items():
    try:
        user = User(config[0], config[1])
        user.start()
        active_users.append(user)
        print(f"✅ Usuario {username} iniciado correctamente")
    except Exception as e:
        print(f"❌ Error iniciando usuario {username}: {e}")

# Endpoint de estado
@app.route('/')
def status():
    status_data = []
    for user in active_users:
        status_data.append({
            "username": user.userdata["username"],
            "balance": user.last_balance,
            "last_error": user.last_error,
            "running": user._running
        })
    return jsonify({"status": "active", "users": status_data})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
