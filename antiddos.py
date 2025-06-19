from scapy.all import sniff
import subprocess
import time

# Лимиты трафика
LIMIT_INCOMING_MB = 3  # Входящий лимит в МБ
LIMIT_OUTGOING_MB = 3  # Исходящий лимит в МБ
CHECK_INTERVAL = 2  # Интервал проверки в секундах

incoming_traffic = {}
outgoing_traffic = {}
blocked_ips = set()

def monitor_packet(packet):
    if not packet.haslayer('IP'):
        return

    src_ip = packet['IP'].src
    dst_ip = packet['IP'].dst
    packet_size_mb = len(packet) / (1024 * 1024)  # размер пакета в МБ

    incoming_traffic[dst_ip] = incoming_traffic.get(dst_ip, 0) + packet_size_mb
    outgoing_traffic[src_ip] = outgoing_traffic.get(src_ip, 0) + packet_size_mb

def block_ip(ip):
    if ip not in blocked_ips:
        try:
            subprocess.run(["iptables", "-A", "INPUT", "-s", ip, "-j", "DROP"], check=True)
            subprocess.run(["iptables", "-A", "OUTPUT", "-d", ip, "-j", "DROP"], check=True)
            blocked_ips.add(ip)
            print(f"[INFO] IP {ip} заблокирован из-за превышения лимита.")
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Ошибка блокировки IP {ip}: {e}")

def check_traffic_limits():
    for ip, traffic in incoming_traffic.items():
        if traffic > LIMIT_INCOMING_MB:
            print(f"[INFO] Входящий трафик для {ip} превышает лимит: {traffic:.2f} МБ.")
            block_ip(ip)

    for ip, traffic in outgoing_traffic.items():
        if traffic > LIMIT_OUTGOING_MB:
            print(f"[INFO] Исходящий трафик для {ip} превышает лимит: {traffic:.2f} МБ.")
            block_ip(ip)

    incoming_traffic.clear()
    outgoing_traffic.clear()

def main():
    print("[INFO] Запуск мониторинга сети...")
    while True:
        sniff(prn=monitor_packet, store=0, timeout=CHECK_INTERVAL)
        check_traffic_limits()
        total_incoming = sum(incoming_traffic.values())
        total_outgoing = sum(outgoing_traffic.values())
        print(f"[INFO] Текущий входящий трафик: {total_incoming:.2f} МБ | Текущий исходящий трафик: {total_outgoing:.2f} МБ")

        # Задержка перед следующей итерацией
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
