import socket
import time
import os
import sqlite3
import json
import subprocess
from threading import Thread, Lock
from database.DataBase import DataBase
from Logic.Device import Device
from Logic.Player import Players
from Logic.LogicMessageFactory import packets
from Utils.Config import Config
from Utils.Helpers import Helpers
from shared import connected_ips

addr = {}
block = []
addr_lock = Lock()

def log_info(*args):
    print('[BİLGİ]', *args)

class Server:
    Clients = {"ClientCounts": 0, "Clients": {}}
    ThreadCount = 0
    MAX_THREADS = 999
    MAX_BYTES_PER_SECOND = 20480

    def __init__(self, ip: str, port: int):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.port = port
        self.ip = ip
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((self.ip, self.port))
        log_info(f'Lobi başlatıldı! {self.ip}:{self.port}')
        self.clear_blocked_ips_in_config()
        self.clear_connected_ips()
        self.setup_database()
        self.total_sent_bytes = 0
        self.total_received_bytes = 0
        self.blocked_ips = set()
        self.reported_blocked_ips = set()
        self.last_warning_time = 0

        Thread(target=self.monitor_load, daemon=True).start()
        Thread(target=self.clean_database_periodically, daemon=True).start()

    def clear_blocked_ips_in_config(self):
        with open('config.json', 'r') as config_file:
            settings = json.load(config_file)
        settings['block'] = []
        with open('config.json', 'w') as config_file:
            json.dump(settings, config_file, indent=4)
        log_info("Sunucu başlatıldığında config.json içindeki engellenmiş IP'ler temizlendi")

    def setup_database(self):
        if os.path.exists("database/Player/plr.db"):
            with sqlite3.connect("database/Player/plr.db") as conn:
                c = conn.cursor()
                c.execute(""" 
                    CREATE TABLE IF NOT EXISTS plrs (
                        token TEXT, lowID INT, name TEXT, trophies INT, gold INT, gems INT, 
                        starpoints INT, tickets INT, Troproad INT, profile_icon INT, 
                        name_color INT, clubID INT, clubRole INT, brawlerData JSON, 
                        brawlerID INT, skinID INT, roomID INT, box INT, bigbox INT, 
                        online INT, vip INT, playerExp INT, friends JSON, SCC TEXT, 
                        trioWINS INT, sdWINS INT, theme INT, BPTOKEN INT, BPXP INT, 
                        quests JSON, freepass INT, buypass INT, notifRead INT, notifRead2 INT,
                        ip_address TEXT, creation_date TEXT, Region TEXT
                    )
                """)
                c.execute("UPDATE plrs SET roomID=0")
                c.execute("UPDATE plrs SET online=0")
                conn.commit()
        else:
            with sqlite3.connect("database/Player/plr.db") as conn:
                c = conn.cursor()
                c.execute(""" 
                    CREATE TABLE IF NOT EXISTS plrs (
                        token TEXT, lowID INT, name TEXT, trophies INT, gold INT, gems INT, 
                        starpoints INT, tickets INT, Troproad INT, profile_icon INT, 
                        name_color INT, clubID INT, clubRole INT, brawlerData JSON, 
                        brawlerID INT, skinID INT, roomID INT, box INT, bigbox INT, 
                        online INT, vip INT, playerExp INT, friends JSON, SCC TEXT, 
                        trioWINS INT, sdWINS INT, theme INT, BPTOKEN INT, BPXP INT, 
                        quests JSON, freepass INT, buypass INT, notifRead INT, notifRead2 INT,
                        ip_address TEXT, creation_date TEXT, Region TEXT
                    )
                """)
                conn.commit()

    def clean_database_periodically(self):
        while True:
            time.sleep(3600)
            try:
                with sqlite3.connect("database/Player/plr.db") as conn:
                    c = conn.cursor()
                    c.execute("DELETE FROM plrs WHERE gold=100 AND trioWINS=0 AND trophies > 0")
                    log_info("Veritabanı botlardan temizlendi.")
                    conn.commit()
            except Exception as e:
                log_info(f"Veritabanı temizleme hatası: {e}")

    def start(self):
        while True:
            self.server.listen()
            try:
                client, address = self.server.accept()
            except Exception as e:
                log_info(f"Bağlantı kabul edilirken hata oluştu: {e}")
                continue

            with addr_lock:
                if Server.ThreadCount >= self.MAX_THREADS:
                    if time.time() - self.last_warning_time > 10:
                        log_info(f"Maksimum thread sayısı aşıldı ({Server.ThreadCount}). Bağlantı kapatıldı.")
                        self.last_warning_time = time.time()
                    client.close()
                    continue

                self.log_connection(address[0])

                if address[0] in self.blocked_ips:
                    if address[0] not in self.reported_blocked_ips:
                        log_info(f"[AntiDDoS] IP engellendi: {address[0]}")
                        self.log_blocked_ip(address[0])
                        self.reported_blocked_ips.add(address[0])
                    client.close()
                    continue

                addr[address[0]] = addr.get(address[0], 0) + 1

                if addr[address[0]] >= 22:
                    if address[0] not in self.blocked_ips:
                        log_info(f"[AntiDDoS] IP'ye karşı koruma etkinleştirildi: {address[0]}")
                        self.blocked_ips.add(address[0])
                        self.update_blocked_clients(address[0])
                    client.close()
                else:
                    connected_ips.add(address[0])
                    ClientThread(client, address, self).start()
                    Server.ThreadCount += 1

    def clear_connected_ips(self):
        with open('JSON/ConnectedIP.json', 'w') as log_file:
            json.dump([], log_file, indent=4)
        log_info("Sunucu başlatıldığında ConnectedIP.json dosyası temizlendi.")

    def log_connection(self, ip):
        moscow_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time() + 3 * 3600))
        with sqlite3.connect("database/Player/plr.db") as conn:
            c = conn.cursor()
            c.execute("SELECT lowID, name FROM plrs WHERE SCC = ?", (ip,))
            result = c.fetchone()

        log_data = {
            "time": moscow_time,
            "ip": ip
        }

        with open('JSON/ConnectedIP.json', 'a') as log_file:
            json.dump(log_data, log_file, ensure_ascii=False, indent=4)
            log_file.write('\n')

        log_info(f"Bağlantı: {log_data}")

    def log_blocked_ip(self, ip):
        with open('JSON/blocked_ips.log', 'a') as log_file:
            log_file.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - IP Engellendi: {ip}\n")

    def update_blocked_clients(self, ip):
        with open('config.json', 'r') as config_file:
            settings = json.load(config_file)
        
        if ip not in settings['block']:
            settings['block'].append(ip)
        
        with open('config.json', 'w') as config_file:
            json.dump(settings, config_file, indent=4)

        log_info(f"Engellenmiş IP'ler: {settings['block']}")

    def monitor_load(self):
        while True:
            time.sleep(3600)
            log_info("Bağlantılar izleniyor...")

class ClientThread(Thread):
    MAX_RECEIVE_BYTES = 10240
    MAX_BYTES_PER_SECOND = 10240

    def __init__(self, client, address, server):
        super().__init__()
        self.client = client
        self.address = address
        self.device = Device(self.client)
        self.player = Players(self.device)
        self.server = server
        self.total_received_bytes = 0
        self.total_sent_bytes = 0
        self.bytes_received_in_last_second = 0
        self.last_packet_time = time.time()
        self.packet_count = 0

    def recvall(self, length):
        data = b''
        while len(data) < length:
            packet = self.client.recv(length - len(data))
            if not packet:
                break
            data += packet
        return data

    def run(self):
        client_ip = self.address[0]
        try:
            client_ip = self.client.getpeername()[0]
            self.player.ip_address = self.client.getpeername()[0]
            while True:
                header = self.client.recv(7)
                if len(header) > 0:
                    packet_id = int.from_bytes(header[:2], 'big')
                    length = int.from_bytes(header[2:5], 'big')
                    data = self.recvall(length)

                    self.total_received_bytes += length
                    self.server.total_sent_bytes += length
                    self.bytes_received_in_last_second += length
                    self.packet_count += 1

                    if time.time() - self.last_packet_time >= 1:
                        if self.bytes_received_in_last_second > self.MAX_BYTES_PER_SECOND:
                            log_info(f"[AntiDDoS] IP {client_ip} sınırı aştı, engelleniyor...")
                            self.server.blocked_ips.add(client_ip)
                            self.server.update_blocked_clients(client_ip)
                            self.client.close()
                            break

                        self.bytes_received_in_last_second = 0
                        self.last_packet_time = time.time()

                    if packet_id in packets:
                        message = packets[packet_id](self.client, self.player, data)
                        message.decode()
                        message.process()
                else:
                    break
        except Exception as e:
            log_info(f"[HATA] İstemcide hata - {client_ip}: {e}")
        finally:
            self.client.close()
            connected_ips.discard(client_ip)
            log_info(f"[BİLGİ] IP {client_ip} bağlantısı kapatıldı")

if __name__ == "__main__":
    server = Server("0.0.0.0", 9339)
    server.start()