#!/bin/bash

# Параметры
IFACE="eth0"  # Укажите имя вашего сетевого интерфейса
LIMIT="50kbit"  # Ограничение скорости

# Удаляем все существующие правила tc
tc qdisc del dev $IFACE root 2> /dev/null

# Добавляем новое правило для ограничения входящего трафика
tc qdisc add dev $IFACE root handle 1: htb default 12
tc class add dev $IFACE parent 1: classid 1:1 htb rate 1mbit
tc class add dev $IFACE parent 1:1 classid 1:12 htb rate $LIMIT ceil $LIMIT
