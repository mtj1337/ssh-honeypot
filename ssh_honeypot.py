import socket
import threading
import requests
from datetime import datetime
import paramiko
import time

# tady das svuj discord webhook
WEBHOOK_URL = "https://discord.com/api/webhooks/ТVUJ_WEBHOOK_SEM"

# na jakem portu poslouchat (2222 nechce root, 22 chce)
PORT = 2222

# po kolika sekundach poslat souhrnnou zpravu
OKNO_SEKUND = 60

# vygeneruj klic: ssh-keygen -t rsa -f server.key
HOST_KEY = paramiko.RSAKey(filename="server.key")

# fronta pokusu cekajicich na odeslani
_zamek = threading.Lock()
_fronta = []


def _odeslat_souhrnnou_zpravu():
    # bezi v pozadi, kazdych OKNO_SEKUND zkontroluje frontu
    while True:
        time.sleep(OKNO_SEKUND)
        with _zamek:
            if not _fronta:
                continue
            pokyny = list(_fronta)
            _fronta.clear()

        if len(pokyny) == 1:
            # jen jeden pokus, posli normalne
            p = pokyny[0]
            zprava = (
                f"**SSH pokus o prihlaseni**\n"
                f"```\n"
                f"Cas:      {p['cas']}\n"
                f"IP:       {p['ip']}:{p['port']}\n"
                f"Uzivatel: {p['uzivatel']}\n"
                f"Heslo:    {p['heslo']}\n"
                f"```"
            )
        else:
            # vice pokusu, posli souhrn
            radky = "\n".join(
                f"{p['cas']}  {p['ip']:<15}  {p['uzivatel']}:{p['heslo']}"
                for p in pokyny
            )
            zprava = (
                f"**SSH souhrn za posledních {OKNO_SEKUND}s ({len(pokyny)} pokusu)**\n"
                f"```\n"
                f"{'Cas':<19}  {'IP':<15}  Uzivatel:Heslo\n"
                f"{'-'*60}\n"
                f"{radky}\n"
                f"```"
            )

        try:
            requests.post(WEBHOOK_URL, json={"content": zprava}, timeout=5)
        except Exception as e:
            print(f"[!] discord chyba: {e}")


def posli_na_discord(ip, port, uzivatel, heslo):
    # prida pokus do fronty, odesle se az v dalsim okne
    cas = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _zamek:
        _fronta.append({"cas": cas, "ip": ip, "port": port, "uzivatel": uzivatel, "heslo": heslo})


class HoneypotServer(paramiko.ServerInterface):
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port

    def check_auth_password(self, username, password):
        print(f"[+] pokus: {self.ip} | {username}:{password}")
        # logujeme ale vzdycky odmitnem
        posli_na_discord(self.ip, self.port, username, password)
        return paramiko.AUTH_FAILED

    def check_channel_request(self, kind, chanid):
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def get_allowed_auths(self, username):
        return "password"


def zpracuj_spojeni(client_socket, adresa):
    ip, port = adresa
    try:
        transport = paramiko.Transport(client_socket)
        transport.add_server_key(HOST_KEY)
        server = HoneypotServer(ip, port)
        transport.start_server(server=server)

        # cekame chvili at stihne poslat credentials
        chan = transport.accept(20)
        if chan:
            chan.close()
    except Exception:
        # ignorujeme chyby (skenery, neplatne pakety atd)
        pass
    finally:
        try:
            client_socket.close()
        except Exception:
            pass


def main():
    # spust vlakno co posilá souhrnne zpravy na discord
    t = threading.Thread(target=_odeslat_souhrnnou_zpravu, daemon=True)
    t.start()

    print(f"[*] honeypot bezi na portu {PORT}")
    print(f"[*] discord zpravy se posilaji kazdych {OKNO_SEKUND}s\n")

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(("0.0.0.0", PORT))
    server_socket.listen(100)

    while True:
        try:
            client, adresa = server_socket.accept()
            # kazde spojeni v novem vlakne
            t = threading.Thread(target=zpracuj_spojeni, args=(client, adresa))
            t.daemon = True
            t.start()
        except KeyboardInterrupt:
            print("\n[*] konec")
            break


if __name__ == "__main__":
    main()
