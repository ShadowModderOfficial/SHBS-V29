import sqlite3
from datetime import datetime, timedelta
import time
import json


class AntiBot:
    def __init__(self):
        self.db_path = "database/Player/plr.db"
        self.club_db_path = "database/Club/clubs.db"
        self.create_free_ids_table()
    
    def create_account(self, name, ip_address):
        """Создаёт новый аккаунт, присваивая ему уникальный lowID."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Проверяем наличие свободных lowID
            cursor.execute("SELECT lowID FROM LowID LIMIT 1")
            free_id = cursor.fetchone()

            if free_id:
                # Если свободный lowID есть, используем его и удаляем из таблицы свободных ID
                low_id = free_id[0]
                cursor.execute("DELETE FROM LowID WHERE lowID = ?", (low_id,))
            else:
            # Если свободных ID нет, используем следующий свободный
                cursor.execute("SELECT MAX(lowID) FROM plrs")
                max_id = cursor.fetchone()[0]
                low_id = max_id + 1 if max_id else 1

            # Вставка нового аккаунта
            cursor.execute("""
                INSERT INTO plrs (lowID, name, ip_address, creation_date) 
                VALUES (?, ?, ?, ?)
            """, (low_id, name, ip_address, datetime.now().strftime("%Y.%m.%d %H:%M:%S")))

            conn.commit()
            conn.close()

            print(f"[AntiBot] Новый аккаунт создан с lowID {low_id}.")

        except sqlite3.Error as e:
            print(f"Ошибка при работе с базой данных: {e}")


    def create_table_if_not_exists(self):
        """Создание таблицы, если она отсутствует."""
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("""
                CREATE TABLE IF NOT EXISTS plrs (
                    token TEXT, 
                    lowID INT, 
                    name TEXT, 
                    trophies INT, 
                    gold INT, 
                    gems INT, 
                    starpoints INT, 
                    tickets INT, 
                    Troproad INT, 
                    profile_icon INT, 
                    name_color INT, 
                    clubID INT, 
                    clubRole INT, 
                    brawlerData JSON, 
                    brawlerID INT, 
                    skinID INT, 
                    roomID INT, 
                    box INT, 
                    bigbox INT, 
                    online INT, 
                    vip INT, 
                    playerExp INT, 
                    friends JSON, 
                    SCC TEXT, 
                    trioWINS INT, 
                    sdWINS INT, 
                    theme INT, 
                    BPTOKEN INT, 
                    BPXP INT, 
                    quests JSON, 
                    freepass INT, 
                    buypass INT, 
                    notifRead INT, 
                    notifRead2 INT,
                    ip_address TEXT, 
                    creation_date TEXT,
                    Region TEXT
                )
            """)
            conn.commit()
            
    def create_free_ids_table(self):
        """Создание таблицы для свободных lowID."""
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("""
                CREATE TABLE IF NOT EXISTS LowID (
                    lowID INT
                )
            """)
            conn.commit()

    def remove_account(self, low_id):
        """Удаляет аккаунт и очищает его из списков друзей у других пользователей."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Добавляем удалённый lowID в таблицу свободных ID
            cursor.execute("INSERT INTO LowID (lowID) VALUES (?)", (low_id,))
            conn.commit()

            # Удаляем аккаунт из базы данных
            cursor.execute("DELETE FROM plrs WHERE lowID = ?", (low_id,))
            conn.commit()

            # Очищаем этого пользователя из списка друзей у других аккаунтов
            cursor.execute("SELECT lowID, friends FROM plrs")
            all_accounts = cursor.fetchall()

            for account in all_accounts:
                friends = json.loads(account[1]) if account[1] else []
                if low_id in friends:
                    friends.remove(low_id)
                    updated_friends = json.dumps(friends)
                    cursor.execute("UPDATE plrs SET friends = ? WHERE lowID = ?", (updated_friends, account[0]))
                    print(f"[AntiBot] Удален lowID {low_id} из списка друзей пользователя {account[0]}.")
        
            conn.commit()
            conn.close()

        except sqlite3.Error as e:
            print(f"Ошибка при работе с базой данных: {e}")

    def check_and_remove(self, ip_address):
        """Удаление аккаунтов с одинаковым IP и учетом условий по имени и времени создания."""
        self.create_table_if_not_exists()  # Создаем таблицу, если ее нет
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

        # Получаем все аккаунты с указанным IP
            cursor.execute("SELECT token, lowID, name, creation_date, ip_address FROM plrs WHERE ip_address = ?", (ip_address,))
            accounts = cursor.fetchall()

            if len(accounts) > 2:  # Если более 2 аккаунтов с одинаковым IP
                for account in accounts:
                    print(f"[AntiBot] Удален аккаунт с lowID {account[1]} (IP: {ip_address})")
                    self.remove_account(account[1])

            # Преобразуем время создания аккаунтов в datetime
            for i in range(len(accounts)):
                accounts[i] = list(accounts[i])  # Преобразуем в изменяемый список
                accounts[i][3] = datetime.strptime(accounts[i][3], "%Y.%m.%d %H:%M:%S")  # creation_date -> datetime

            # Проверяем и удаляем аккаунты с именем "VBC26", созданные в одну и ту же секунду, независимо от IP
            cursor.execute("SELECT token, lowID, name, creation_date, ip_address FROM plrs WHERE name = 'VBC26'")
            vbc26_accounts = cursor.fetchall()

            for i in range(len(vbc26_accounts)):
                vbc26_accounts[i] = list(vbc26_accounts[i])  # Преобразуем в изменяемый список
                vbc26_accounts[i][3] = datetime.strptime(vbc26_accounts[i][3], "%Y.%m.%d %H:%M:%S")  # creation_date -> datetime

            # Группируем аккаунты с одинаковым временем создания
            grouped_by_creation_time = {}
            for account in vbc26_accounts:
                creation_time = account[3]
                grouped_by_creation_time.setdefault(creation_time, []).append(account)

            # Удаляем все аккаунты, созданные в одно и то же время (если их больше одного)
            for creation_time, group in grouped_by_creation_time.items():
                if len(group) > 1:
                    for account in group:
                        print(f"[AntiBot] Удален аккаунт VBC26 с lowID {account[1]} (IP: {account[4]}, Время: {creation_time})")
                        self.remove_account(account[1])

            conn.close()

        except sqlite3.Error as e:
            print(f"Ошибка при работе с базой данных: {e}")


    def check_all_ips(self):
        """Проверка всех уникальных IP-адресов в базе данных."""
        self.create_table_if_not_exists()  # Создаем таблицу, если ее нет
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Получаем все уникальные IP-адреса
            cursor.execute("SELECT DISTINCT ip_address FROM plrs")
            ip_addresses = cursor.fetchall()

            if not ip_addresses:
                conn.close()
                return

            # Проверяем каждый IP
            for ip_address in ip_addresses:
                self.check_and_remove(ip_address[0])

            conn.close()

        except sqlite3.Error as e:
            print(f"Ошибка при работе с базой данных: {e}")
            
    def delete_club_if_contains_deleted_account(self):
        """Удаляет клубы, если в них есть участники с удаленными аккаунтами."""
        try:
            conn_players = sqlite3.connect(self.player_db_path)
            conn_clubs = sqlite3.connect(self.club_db_path)
            cursor_players = conn_players.cursor()
            cursor_clubs = conn_clubs.cursor()

            # Получаем все клубы
            cursor_clubs.execute("SELECT clubID, members FROM clubs")
            clubs = cursor_clubs.fetchall()

            for club in clubs:
                club_id, members_json = club

                try:
                    # Загружаем список участников клуба
                    members = json.loads(members_json).get("members", [])
                except json.JSONDecodeError:
                    print(f"[Ошибка] Клуб {club_id} имеет некорректные данные о членах.")
                    continue

                # Проверяем, существуют ли все участники клуба
                for member_id in members:
                    cursor_players.execute("SELECT lowID FROM plrs WHERE lowID = ?", (member_id,))
                    if cursor_players.fetchone() is None:  # Если участник не найден
                        cursor_clubs.execute("DELETE FROM clubs WHERE clubID = ?", (club_id,))
                        print(f"[AntiBot] Клуб с ID {club_id} удален, так как в нем есть удаленный аккаунт {member_id}.")
                        break  # Удалили клуб, проверку можно прекратить

            conn_players.commit()
            conn_clubs.commit()
            conn_players.close()
            conn_clubs.close()

        except sqlite3.Error as e:
            print(f"Ошибка при работе с базой данных: {e}")

    def run_monitor(self, interval=1):
        """Мониторинг базы данных с заданным интервалом."""
        try:
            while True:
                self.check_all_ips()
                time.sleep(interval)
        except KeyboardInterrupt:
            print("Мониторинг остановлен.")


if __name__ == "__main__":
    anti_bot = AntiBot()
    anti_bot.run_monitor(interval=1)
