# Hosts (contenedores Docker)

Fuente: sección Plan de direccionamiento de `docs/especificacion.md`.

| Host | Segmento | IPv4 / gateway | IPv6 / gateway | DNS |
| --- | --- | --- | --- | --- |
| SRV-DMZ | DMZ | 10.50.1.34/28, gw 10.50.1.33 | 2001:db8:105:30::10/64, gw 2001:db8:105:30::1 | él mismo |
| PC-EXT | Red externa A | 198.51.100.10/24, gw 198.51.100.1 | 2001:db8:ffff:100::10/64, gw fe80::1 | 203.0.113.20 y 2001:db8:105:30::10 |
| PC-EXT-WEB | Red externa B | 192.0.2.10/24, gw 192.0.2.1 | 2001:db8:ffff:200::10/64, gw fe80::1 | 203.0.113.20 y 2001:db8:105:30::10 |
| PC-USER | VLAN 10 | 10.50.0.10/24, gw 10.50.0.1 | SLAAC en 2001:db8:105:10::/64, gw por RA | 10.50.1.34 y 2001:db8:105:30::10 |
| PC-ADMIN | VLAN 20 | 10.50.1.10/27, gw 10.50.1.1 | 2001:db8:105:20::10/64, gw fe80::1 | 10.50.1.34 y 2001:db8:105:30::10 |

## Configuración de red en GNS3

En cada contenedor: clic derecho → Edit network configuration. Estado: **pendiente de probar en la maqueta**. Al confirmarlo, reemplazá cada bloque por el que realmente funcionó.

Antes de configurar IPv6, verificá que el contenedor lo tenga habilitado (`sysctl net.ipv6.conf.eth0.disable_ipv6` debe dar 0) y, en PC-USER, que acepte RA (`accept_ra` en 1).

### SRV-DMZ

Usa la imagen `caso-e/srv-dmz`, que ya trae bind9, nginx y SSH configurados. Cómo construirla y crear la plantilla está en `servicios/README.md`.

```
auto eth0
iface eth0 inet static
	address 10.50.1.34
	netmask 255.255.255.240
	gateway 10.50.1.33
	up echo nameserver 10.50.1.34 > /etc/resolv.conf

iface eth0 inet6 static
	address 2001:db8:105:30::10
	netmask 64
	gateway 2001:db8:105:30::1
```

### PC-EXT

```
auto eth0
iface eth0 inet static
	address 198.51.100.10
	netmask 255.255.255.0
	gateway 198.51.100.1
	up printf 'nameserver 203.0.113.20\nnameserver 2001:db8:105:30::10\n' > /etc/resolv.conf

iface eth0 inet6 static
	address 2001:db8:ffff:100::10
	netmask 64
	gateway fe80::1
```

### PC-EXT-WEB

```
auto eth0
iface eth0 inet static
	address 192.0.2.10
	netmask 255.255.255.0
	gateway 192.0.2.1
	up printf 'nameserver 203.0.113.20\nnameserver 2001:db8:105:30::10\n' > /etc/resolv.conf

iface eth0 inet6 static
	address 2001:db8:ffff:200::10
	netmask 64
	gateway fe80::1
```

### PC-USER

```
auto eth0
iface eth0 inet static
	address 10.50.0.10
	netmask 255.255.255.0
	gateway 10.50.0.1
	up printf 'nameserver 10.50.1.34\nnameserver 2001:db8:105:30::10\n' > /etc/resolv.conf

iface eth0 inet6 auto
```

Dirección SLAAC real (anotar con `ip -6 addr` antes de E01): `pendiente`

### PC-ADMIN

```
auto eth0
iface eth0 inet static
	address 10.50.1.10
	netmask 255.255.255.224
	gateway 10.50.1.1
	up printf 'nameserver 10.50.1.34\nnameserver 2001:db8:105:30::10\n' > /etc/resolv.conf

iface eth0 inet6 static
	address 2001:db8:105:20::10
	netmask 64
	gateway fe80::1
```
