#!/bin/sh
# SRV-DMZ — arranque de servicios dentro del contenedor de GNS3.
# GNS3 configura eth0 con /etc/network/interfaces y después ejecuta este script.

# Espera hasta 30 s a que eth0 tenga la IP de la DMZ (en Docker local puede no tenerla nunca).
i=0
while [ $i -lt 30 ] && ! ip addr show eth0 2>/dev/null | grep -q "10.50.1.34"; do
    sleep 1
    i=$((i + 1))
done

/usr/sbin/sshd
named -u named -c /etc/bind/named.conf
nginx

echo "SRV-DMZ: sshd, named y nginx iniciados"
ip -brief address show eth0 2>/dev/null

# Deja una consola para GNS3.
exec /bin/sh
