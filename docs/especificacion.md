# Caso E - Especificación de topología

Oct 18, 2026 · Grupo 5

## Resumen y supuestos

La empresa publica DNS y HTTP desde una DMZ hacia una red externa simulada, y la LAN interna nunca queda expuesta. El FortiGate es el único punto de paso entre las tres zonas (WAN, LAN y DMZ). Las ACL de router cubren el tráfico que el firewall no ve.

Este documento define la topología completa sin comandos. Las configuraciones de cada equipo se escriben después, a partir de estas tablas.

**Supuestos de diseño**

- **Bloque del grupo:** 10.50.0.0/16, 2001:db8:105::/48 y zona `g5.eif101o.test`. Es la quinta fila del enunciado, por confirmar con el profesor.
- **Red externa simulada:** usa rangos de documentación (RFC 5737): 203.0.113.0/24, 198.51.100.0/24 y 192.0.2.0/24. En IPv6, el "proveedor" usa 2001:db8:ffff::/48, fuera del /48 del grupo.
- **Imágenes:**
  - Routers Cisco IOSv, interfaces Gi0/0 a Gi0/3.
  - FortiGate VM, port1 a port3.
  - Switches Ethernet integrados de GNS3.
  - Hosts como contenedores Docker.

  Si la OVA trae otras imágenes, solo cambian los nombres de interfaz.
- **Tamaño:** 11 nodos, dentro del perfil sugerido. Son 1 FortiGate, 3 routers, 2 switches, 4 hosts cliente y 1 servidor Linux.

**Principios que guían el diseño**

1. **IPv4:** la LAN usa direcciones privadas que nunca se anuncian hacia afuera. Lo que sale pasa por NAT y lo que entra solo llega a la DMZ por VIP.
2. **IPv6:** no hay NAT66. El /48 completo se enruta hasta el ISP, así que la única protección de la LAN es la política del FortiGate.
3. **Defensa en profundidad:** el firewall controla el tráfico entre zonas. Las ACL controlan el borde (anti-spoofing) y el tráfico entre VLAN internas, que nunca pasa por el firewall.

**Vista general**

&#91;embedded content: Topología del caso E · 11 nodos, 10 enlaces, 3 zonas\]

Las líneas son los 10 enlaces de la tabla de cableado. El FortiGate (resaltado) es el único equipo que toca las tres zonas.

## Inventario de equipos

Cada nodo responde a un requisito del caso E. No hay equipos de relleno, que es lo que evalúa el punto 6 de la defensa.

| Equipo | Tipo / imagen | Zona | Rol |
| --- | --- | --- | --- |
| R-ISP | Cisco IOSv | Externa | Simula Internet. Conecta a los clientes externos y enruta los prefijos públicos de la empresa |
| R-EDGE | Cisco IOSv | Borde | Router de borde de la empresa. Lleva la ACL anti-spoofing hacia el ISP. Se gestiona solo por consola |
| FGT-01 | FortiGate VM | WAN, LAN y DMZ | Firewall de zonas: VIP, NAT de salida, políticas y logs (disco local y syslog). Habla OSPF con R-LAN |
| R-LAN | Cisco IOSv | LAN | Router interno en router-on-a-stick para las VLAN 10 y 20. Habla OSPF y lleva la ACL de segmentación y la de gestión (vty) |
| SW-LAN | Switch Ethernet de GNS3 | LAN | Troncal 802.1Q hacia R-LAN y puertos de acceso para las VLAN 10 y 20 |
| SW-DMZ | Switch Ethernet de GNS3 | DMZ | Segmento DMZ. Permite sumar servidores sin tocar el FortiGate |
| SRV-DMZ | Docker Linux (Alpine o Debian) | DMZ | DNS autoritativo (bind9) y HTTP (nginx). Es el servicio publicado |
| PC-EXT | Docker Alpine con dig y curl | Externa | Cliente de pruebas desde Internet: DNS, HTTP e intentos que deben bloquearse |
| PC-EXT-WEB | Docker Webterm (Firefox) | Externa | Navegador para mostrar la página por nombre en la defensa |
| PC-USER | Docker Alpine con dig, curl y ssh | LAN, VLAN 10 | Usuario interno. Prueba el consumo permitido y el SSH denegado |
| PC-ADMIN | Docker con terminal y navegador | LAN, VLAN 20 | Administración del servidor (SSH), de R-LAN (SSH) y del FortiGate (GUI). Recibe el syslog del FortiGate y de R-LAN |

## Cableado

Son 10 enlaces. La maqueta se arma exactamente con este mapa para que todos tengan los mismos puertos y las configuraciones sirvan sin cambios.

| # | Equipo A | Puerto A | Equipo B | Puerto B | Segmento |
| --- | --- | --- | --- | --- | --- |
| 1 | R-ISP | Gi0/0 | R-EDGE | Gi0/0 | Enlace ISP |
| 2 | R-ISP | Gi0/1 | PC-EXT | eth0 | Red externa A |
| 3 | R-ISP | Gi0/2 | PC-EXT-WEB | eth0 | Red externa B |
| 4 | R-EDGE | Gi0/1 | FGT-01 | port1 | WAN pública de la empresa |
| 5 | FGT-01 | port2 | R-LAN | Gi0/0 | Tránsito LAN |
| 6 | FGT-01 | port3 | SW-DMZ | puerto 0 | DMZ |
| 7 | SW-DMZ | puerto 1 | SRV-DMZ | eth0 | DMZ |
| 8 | R-LAN | Gi0/1 | SW-LAN | puerto 0 | Troncal 802.1Q |
| 9 | SW-LAN | puerto 1 | PC-USER | eth0 | VLAN 10 Usuarios |
| 10 | SW-LAN | puerto 2 | PC-ADMIN | eth0 | VLAN 20 Admin |

**Puertos de los switches**

| Switch | Puerto | Modo | VLAN |
| --- | --- | --- | --- |
| SW-LAN | 0 | dot1q (troncal) | 10 y 20 etiquetadas |
| SW-LAN | 1 | access | 10 |
| SW-LAN | 2 | access | 20 |
| SW-DMZ | 0 y 1 | access | 1 (segmento plano) |

**Notas sobre las interfaces**

- **R-LAN Gi0/1:** no lleva IP en la interfaz física. Las puertas de enlace viven en las subinterfaces Gi0/1.10 y Gi0/1.20.
- **Roles del FortiGate:** port1 es WAN, port2 es LAN y port3 es DMZ. Son tres interfaces, el máximo si la licencia es de evaluación.
- **Administración inicial:** todos los equipos se configuran primero por la consola de GNS3. Así no se necesita una red de gestión aparte.

## Plan de direccionamiento

Lo interno sale de 10.50.0.0/16 con VLSM, asignado de mayor a menor y de forma contigua. Queda libre todo desde 10.50.1.52 en adelante para crecer.

En IPv6 cada segmento recibe un /64 del /48 del grupo. El identificador de subred repite el número de VLAN (10, 20) o de zona (30 = DMZ), y los enlaces usan ff00 y ff01 para leerse de un vistazo.

**Segmentos internos (VLSM)**

Los hosts necesarios son el dimensionamiento supuesto. El grupo los ajusta si cambia el escenario.

| Segmento | Hosts necesarios | IPv4 | Máscara | Rango útil | Broadcast | IPv6 |
| --- | --- | --- | --- | --- | --- | --- |
| VLAN 10 Usuarios | hasta 200 | 10.50.0.0/24 | 255.255.255.0 | 10.50.0.1 – .0.254 | 10.50.0.255 | 2001:db8:105:10::/64 |
| VLAN 20 Admin | hasta 25 | 10.50.1.0/27 | 255.255.255.224 | 10.50.1.1 – .1.30 | 10.50.1.31 | 2001:db8:105:20::/64 |
| DMZ | hasta 10 | 10.50.1.32/28 | 255.255.255.240 | 10.50.1.33 – .1.46 | 10.50.1.47 | 2001:db8:105:30::/64 |
| Tránsito FGT–R-LAN | 2 | 10.50.1.48/30 | 255.255.255.252 | 10.50.1.49 – .1.50 | 10.50.1.51 | 2001:db8:105:ff00::/64 |
| Reserva | - | 10.50.1.52 en adelante | - | - | - | resto del /48 |

**Segmentos externos (rangos de documentación)**

| Segmento | IPv4 | IPv6 | Comentario |
| --- | --- | --- | --- |
| WAN pública de la empresa | 203.0.113.16/29 | 2001:db8:105:ff01::/64 | Aquí vive el VIP 203.0.113.20 |
| Enlace ISP | 203.0.113.0/30 | 2001:db8:ffff:1::/64 | Espacio del proveedor |
| Red externa A | 198.51.100.0/24 | 2001:db8:ffff:100::/64 | PC-EXT |
| Red externa B | 192.0.2.0/24 | 2001:db8:ffff:200::/64 | PC-EXT-WEB |

**Direcciones por interfaz**

| Equipo | Interfaz | IPv4 | IPv6 global | Link-local |
| --- | --- | --- | --- | --- |
| R-ISP | Gi0/0 | 203.0.113.1/30 | 2001:db8:ffff:1::1/64 | fe80::1 |
| R-ISP | Gi0/1 | 198.51.100.1/24 | 2001:db8:ffff:100::1/64 | fe80::1 |
| R-ISP | Gi0/2 | 192.0.2.1/24 | 2001:db8:ffff:200::1/64 | fe80::1 |
| R-EDGE | Gi0/0 | 203.0.113.2/30 | 2001:db8:ffff:1::2/64 | fe80::2 |
| R-EDGE | Gi0/1 | 203.0.113.17/29 | 2001:db8:105:ff01::1/64 | fe80::1 |
| FGT-01 | port1 (WAN) | 203.0.113.18/29 | 2001:db8:105:ff01::2/64 | automática (EUI-64) |
| FGT-01 | VIP | 203.0.113.20 → 10.50.1.34 | - | - |
| FGT-01 | port2 (LAN) | 10.50.1.49/30 | 2001:db8:105:ff00::1/64 | automática |
| FGT-01 | port3 (DMZ) | 10.50.1.33/28 | 2001:db8:105:30::1/64 | automática |
| R-LAN | Gi0/0 | 10.50.1.50/30 | 2001:db8:105:ff00::2/64 | fe80::2 |
| R-LAN | Gi0/1.10 | 10.50.0.1/24 | 2001:db8:105:10::1/64 | fe80::1 |
| R-LAN | Gi0/1.20 | 10.50.1.1/27 | 2001:db8:105:20::1/64 | fe80::1 |

**Hosts**

| Host | IPv4 / gateway | IPv6 / gateway | DNS configurado |
| --- | --- | --- | --- |
| SRV-DMZ | 10.50.1.34/28, gw 10.50.1.33 | 2001:db8:105:30::10/64 (fija), gw 2001:db8:105:30::1 | él mismo |
| PC-EXT | 198.51.100.10/24, gw .1 | 2001:db8:ffff:100::10/64, gw fe80::1 | 203.0.113.20 y 2001:db8:105:30::10 |
| PC-EXT-WEB | 192.0.2.10/24, gw .1 | 2001:db8:ffff:200::10/64, gw fe80::1 | 203.0.113.20 y 2001:db8:105:30::10 |
| PC-USER | 10.50.0.10/24, gw .1 | **SLAAC** sobre 2001:db8:105:10::/64, gw aprendido por RA (fe80::1) | 10.50.1.34 y 2001:db8:105:30::10 |
| PC-ADMIN | 10.50.1.10/27, gw .1 | 2001:db8:105:20::10/64 (fija), gw fe80::1 | 10.50.1.34 y 2001:db8:105:30::10 |

**Rol de las direcciones link-local**

- **OSPFv3:** las adyacencias se forman y anuncian sobre las link-local. Los next-hop IPv6 que aprende cada router son las link-local del vecino, no las globales.
- **Puerta de enlace por RA:** con SLAAC, PC-USER aprende la link-local del router como gateway.
- **Por qué fe80::1 fija:** los routers Cisco la llevan manual en los gateways para que las tablas y capturas se lean fácil. Se repite en varios enlaces sin conflicto, porque una link-local solo existe dentro de su enlace.
- **FortiGate:** usa link-local automáticas. Se documentan con la salida real del equipo.

## Enrutamiento

La red interna (FGT-01 y R-LAN) usa OSPFv2 y OSPFv3 en área 0. Del FortiGate hacia afuera todo es estático, como pasa con un proveedor real. R-EDGE y R-ISP nunca conocen 10.50.0.0/16: esa red solo existe detrás del NAT.

**OSPF (dinámico)**

| Parámetro | FGT-01 | R-LAN |
| --- | --- | --- |
| Router-ID (OSPFv2 y OSPFv3) | 5.5.5.1 | 5.5.5.2 |
| Área | 0 | 0 |
| Interfaces activas (forman vecindad) | port2 | Gi0/0 |
| Interfaces pasivas (se anuncian, sin vecinos) | port3 (DMZ) | Gi0/1.10, Gi0/1.20 |
| Ruta por defecto | La inyecta en OSPF (default-information originate) | La aprende como externa (O\*E2) |

Se usa un área única porque el foco del caso E es seguridad. Hay solo dos routers OSPF y un área extra no aportaría una función demostrable.

OSPF en lugar de estáticas internas tiene dos ventajas. Una VLAN nueva en R-LAN se anuncia sola. Y la caída del enlace FGT–R-LAN es una falla controlada que se puede mostrar en la defensa.

**Rutas estáticas**

| Equipo | Destino | Next-hop | Distancia | Propósito |
| --- | --- | --- | --- | --- |
| FGT-01 | 0.0.0.0/0 | 203.0.113.17 | 10 (por defecto en FortiOS) | Salida a Internet |
| FGT-01 | ::/0 | 2001:db8:105:ff01::1 | 10 | Salida a Internet IPv6 |
| R-EDGE | 0.0.0.0/0 | 203.0.113.1 | 1 | Salida hacia el ISP |
| R-EDGE | ::/0 | 2001:db8:ffff:1::1 | 1 | Salida IPv6 hacia el ISP |
| FGT-01 | 10.50.0.0/16 | blackhole | 254 | Descartar destinos internos que no existen. Sin ella, la política 4 los sacaría a Internet con SNAT |
| FGT-01 | 2001:db8:105::/48 | blackhole | 254 | Igual en IPv6. Sin ella, un /64 inexistente rebota entre el FGT y R-EDGE (que devuelve el /48 al FGT) |
| R-EDGE | 2001:db8:105::/48 | 2001:db8:105:ff01::2 | 1 | Entregar el prefijo IPv6 de la empresa al FortiGate |
| R-ISP | 203.0.113.16/29 | 203.0.113.2 | 1 | Alcanzar el segmento público (VIP) de la empresa |
| R-ISP | 2001:db8:105::/48 | 2001:db8:ffff:1::2 | 1 | Alcanzar el prefijo IPv6 de la empresa |

**Tablas de rutas esperadas**

| Equipo | IPv4 | IPv6 |
| --- | --- | --- |
| R-LAN | C 10.50.0.0/24, C 10.50.1.0/27, C 10.50.1.48/30, O 10.50.1.32/28 vía 10.50.1.49, O\*E2 0.0.0.0/0 vía 10.50.1.49 | C :10::/64, C :20::/64, C :ff00::/64, O :30::/64 vía link-local del FGT, OE2 ::/0 vía link-local del FGT |
| FGT-01 | S 0.0.0.0/0, S 10.50.0.0/16 (blackhole), C 203.0.113.16/29, C 10.50.1.48/30, C 10.50.1.32/28, O 10.50.0.0/24 y O 10.50.1.0/27 vía 10.50.1.50 | S ::/0, S 2001:db8:105::/48 (blackhole), C :ff01::/64, C :ff00::/64, C :30::/64, O :10::/64 y O :20::/64 vía link-local de R-LAN |
| R-EDGE | S 0.0.0.0/0, C 203.0.113.0/30, C 203.0.113.16/29 | S ::/0, S 2001:db8:105::/48, C :ffff:1::/64, C :105:ff01::/64 |
| R-ISP | C 203.0.113.0/30, C 198.51.100.0/24, C 192.0.2.0/24, S 203.0.113.16/29 | C :ffff:1::/64, C :ffff:100::/64, C :ffff:200::/64, S 2001:db8:105::/48 |

(":10::/64" abrevia 2001:db8:105:10::/64, y así con los demás.)

Las blackhole no tapan a las rutas OSPF: por prefijo más largo, 10.50.0.0/24 gana sobre 10.50.0.0/16. Solo se usan cuando el destino no existe o cuando OSPF cae (F02). Tampoco se redistribuyen en OSPF.

**Recorrido de una consulta externa**

- **IPv4:** PC-EXT → R-ISP → R-EDGE (la /29 está conectada) → FGT-01. El FortiGate responde ARP por el VIP .20, traduce a 10.50.1.34 y entrega en la DMZ.
- **IPv6:** el mismo camino, pero R-EDGE usa la estática del /48. El FortiGate entrega a 2001:db8:105:30::10 sin traducción.
- **Respuesta:** en ambas familias vuelve por la sesión que el FortiGate ya tiene abierta (inspección con estado).

## FortiGate: zonas, NAT y políticas

FGT-01 decide todo el tráfico entre WAN, LAN y DMZ. Lo hace con seis políticas explícitas, evaluadas en orden, y la denegación implícita registrada. En IPv4 publica el servidor por VIP; en IPv6 lo publica por enrutamiento directo, sin NAT66.

**Interfaces y acceso administrativo**

| Interfaz | Alias | Rol | Acceso administrativo |
| --- | --- | --- | --- |
| port1 | WAN | wan | Solo ping. Sin HTTPS ni SSH desde afuera |
| port2 | LAN | lan | HTTPS, SSH y ping |
| port3 | DMZ | dmz | Solo ping |

La cuenta admin queda limitada por *trusted hosts* a 10.50.1.0/27 y 2001:db8:105:20::/64. Aunque PC-USER llegue a port2, el FortiGate no responde a su intento de acceso administrativo (prueba E13).

- **Todas las cuentas con trusted hosts.** El FortiGate solo ignora a los hosts no confiables cuando *todas* las cuentas de administrador tienen trusted hosts. Basta una cuenta sin ellos para que responda a cualquiera. Se revisa también la cuenta creada por defecto.
- **Log de local-in.** Los intentos de gestión denegados (como E11) no pasan por una política de reenvío, así que no aparecen en Forward Traffic. Se activa el log de denegaciones local-in para que queden en el registro.

**Objetos de dirección**

| Objeto | Valor |
| --- | --- |
| NET-USUARIOS | 10.50.0.0/24 y 2001:db8:105:10::/64 |
| NET-ADMIN | 10.50.1.0/27 y 2001:db8:105:20::/64 |
| NET-LAN (grupo) | NET-USUARIOS + NET-ADMIN |
| SRV-DMZ | 10.50.1.34/32 y 2001:db8:105:30::10/128 |
| VIP-SRV-DMZ | 203.0.113.20 en port1 → 10.50.1.34 (NAT estático 1:1) |

El VIP es 1:1 y no por puerto. Así la restricción de servicios queda visible en un solo lugar, la política 1, y se explica mejor en la defensa.

**NAT**

- **Entrada IPv4:** destino traducido por VIP-SRV-DMZ.
- **Salida IPv4:** la política 4 traduce el origen a la IP de port1 (203.0.113.18).
- **IPv6:** sin NAT en ningún sentido. Las direcciones globales viajan tal cual y la política es el único control.

**Políticas en orden de evaluación**

| ID | Nombre | Entrada → Salida | Origen | Destino | Servicio | Acción | NAT | Log | Justificación |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | PUB-DNS-HTTP | port1 → port3 | all | VIP-SRV-DMZ, SRV-DMZ (v6) | DNS, HTTP | Permitir | DNAT por VIP | Todas las sesiones | Publicación controlada hacia la red externa |
| 2 | ADMIN-A-DMZ | port2 → port3 | NET-ADMIN | SRV-DMZ | SSH, DNS, HTTP, PING | Permitir | No | Todas las sesiones | Única zona autorizada para administrar el servidor |
| 3 | USUARIOS-A-DMZ | port2 → port3 | NET-USUARIOS | SRV-DMZ | DNS, HTTP | Permitir | No | Todas las sesiones | Consumo interno del servicio, sin gestión |
| 4 | LAN-A-INTERNET | port2 → port1 | NET-LAN | all | HTTP, HTTPS, DNS, PING | Permitir | SNAT a port1 (solo IPv4) | Seguridad | Salida de la LAN a Internet |
| 5 | DENY-EXT-A-LAN | port1 → port2 | all | all | ALL | Denegar | - | Violaciones | La LAN no queda expuesta (requisito central) |
| 6 | DENY-DMZ-A-LAN | port3 → port2 | all | all | ALL | Denegar | - | Violaciones | Un servidor comprometido no puede saltar a la LAN |
| - | Implícita | cualquiera | all | all | ALL | Denegar | - | Violaciones activado | Todo lo demás |

Cada política cubre IPv4 e IPv6 a la vez, algo que FortiOS 6.4 y posteriores permiten. Con una versión anterior se duplican en un juego IPv6.

Las políticas 5 y 6 son redundantes con la implícita a propósito. El enunciado pide una denegación explícita, y así el log muestra el ID y el nombre de la política que bloqueó.

**Evidencia que se conserva**

- **Logs:** Forward Traffic filtrado por ID de política, más Local Traffic para los accesos administrativos denegados.
- **Contadores:** los hits de cada política.
- **Sesiones:** la tabla de sesiones mientras corren las pruebas.
- **Contadores de ACL:** las líneas de denegación de las ACL llevan `log`, así que el router también deja registro de cada bloqueo.

**Dónde se conservan los logs**

| Origen | Almacenamiento | Por qué |
| --- | --- | --- |
| FGT-01 | Disco local de logs (el disco vacío de 30 GB que trae la plantilla de GNS3) | Sin disco, los logs quedan en memoria y se pierden al apagar la VM |
| FGT-01 | Copia por syslog (UDP 514) a PC-ADMIN | Sobrevive aunque el FortiGate se reinicie. El tráfico lo origina el propio FGT, así que no necesita política |
| R-LAN | Buffer local y syslog a PC-ADMIN | Evidencia de las ACL con fecha y hora |
| R-EDGE | Solo buffer local (`show logging`) | Está fuera del NAT: mandar syslog a la LAN obligaría a abrir un hueco WAN → LAN, justo lo que el caso prohíbe |

El syslog no va a SRV-DMZ: es el servidor expuesto, y si alguien lo compromete podría borrar la evidencia. Todos los equipos usan la misma hora (ajustada a mano o por NTP) para poder cruzar los logs del firewall con los del router.

**Plan B si la licencia es de prueba**

La licencia de prueba permanente de FortiOS (7.2.1 en adelante) limita las políticas de firewall. Medido en el FGT-01 con FortiOS 8.0.0: acepta 3 políticas y rechaza la cuarta con "reached the maximum number of entries". Las cuatro rutas estáticas (dos IPv4 y dos IPv6) y las tres interfaces del diseño se aplicaron sin error. El diseño normal usa 6 políticas, así que se reduce a esto:

1. Las políticas 1 y 3 se fusionan en la 1, DNS-HTTP-A-DMZ: port1 y port2 hacia port3, solo DNS y HTTP, con la IP real del servidor como destino. Una política admite varias interfaces de origen.
   FortiOS no deja mezclar un VIP con un objeto normal en el destino de una política (probado en el FGT-01: "entry not found in datasource"), ni crear un VIP cuya IP externa sea igual a la mapeada. Por eso el plan B activa `central-nat`: el VIP VIP-SRV-DMZ solo hace el DNAT de 203.0.113.20 hacia 10.50.1.34 y la política evalúa el tráfico ya traducido, así un mismo objeto de destino sirve a los externos (por el VIP) y a los usuarios (directo a la IP real, como indica la zona DNS interna).
2. La política 2 (ADMIN-A-DMZ) queda igual, así que el SSH sigue siendo exclusivo de Administración y lo hace cumplir el firewall.
3. Las políticas 5 y 6 se fusionan en la 3, DENY-A-LAN: port1 y port3 hacia port2, denegar todo, con log.
4. La salida a Internet (política 4) se elimina porque el caso no la exige.
5. Las dos rutas blackhole se conservan: no cuentan contra el límite y siguen descartando los destinos internos inexistentes (E15).

Las ACL de los routers no cambian. Con el plan B, el externo hacia la LAN (E01) y la DMZ hacia la LAN (E09) los registra la política 3, y la política 1 atiende el DNS y el HTTP de los usuarios (E06). El SSH externo (E03), el SSH de usuarios al servidor (E05) y el servidor hacia Internet (E14) caen en la denegación implícita, que sigue registrada. El simulador verifica este plan por separado.

Cambiar de plan es una línea: `plan_b` en `automatizacion/topologia/proyecto.yml` (queda en `true` porque el límite de 3 políticas está medido en este FortiGate).

## ACL de router

Hay tres ACL, cada una en IPv4 e IPv6, y todas cubren huecos que el FortiGate no puede ver.

- **R-LAN:** segmenta las VLAN. El tráfico entre la 10 y la 20 se enruta dentro de R-LAN y nunca llega al firewall.
- **R-EDGE:** filtra en el borde lo que no tiene sentido que entre a la empresa, antes de que consuma recursos del FortiGate.
- **Gestión de los routers (vty):** un usuario que hace SSH a su propio gateway (10.50.0.1) habla directo con R-LAN, sin pasar por el firewall. Sin esta ACL, cualquiera de la VLAN 10 podría intentar administrar el router.

Las líneas de denegación llevan `log`, para que el router deje su propio registro además de los contadores.

**ACL-SEG-USUARIOS: R-LAN, entrada en Gi0/1.10**

| Línea | Acción | Origen | Destino | Protocolo | Motivo |
| --- | --- | --- | --- | --- | --- |
| 10 | Permitir | NET-USUARIOS | NET-ADMIN | ICMP echo-reply | Que Admin pueda hacer ping a Usuarios y reciba la respuesta |
| 20 | Permitir | NET-USUARIOS | NET-ADMIN | TCP established | Respuestas a conexiones que inicia Admin |
| 30 | Denegar (log) | NET-USUARIOS | NET-ADMIN | IP (todo) | Usuarios no inician nada hacia Administración |
| 40 | Permitir | any | any | IP (todo) | El resto del tráfico de usuarios sigue al FortiGate |

La versión IPv6 es igual, con 2001:db8:105:10::/64 → 2001:db8:105:20::/64. Neighbor Discovery queda permitido por la línea final.

Las líneas 10 y 20 existen porque la ACL no tiene estado. Sin ellas, Admin no recibiría las respuestas de los usuarios. Esa diferencia con el FortiGate es justo lo que hay que mostrar en la defensa.

La línea 20 tiene una limitación conocida: `established` solo mira si el segmento TCP trae ACK o RST. Un usuario que forje un segmento con ACK lo hace llegar a la VLAN 20. El host lo descarta porque no tiene una conexión abierta, pero la ACL no lo frena. Se deja así a propósito, porque muestra por qué el control fino entre zonas lo hace el firewall con estado. La alternativa en el router sería una ACL reflexiva o un firewall por zonas (ZBF), que no se implementan.

**ACL-VTY-ADMIN: R-LAN, access-class en las líneas vty (IPv4 e IPv6)**

| Línea | Acción | Origen | Motivo |
| --- | --- | --- | --- |
| 10 | Permitir | NET-ADMIN (10.50.1.0/27 y 2001:db8:105:20::/64) | Única zona autorizada para administrar el router |
| 20 | Denegar (log) | any | Cualquier otro intento de SSH queda registrado |

Las vty aceptan solo SSH (`transport input ssh`), nunca Telnet. **R-EDGE** se gestiona solo por consola: sus vty niegan todo. Desde afuera ya lo bloquea la línea 30 de ACL-BORDE-IN, y desde la LAN llegaría con la IP traducida del FortiGate, así que no hay un origen legítimo que permitir.

**ACL-BORDE-IN: R-EDGE, entrada en Gi0/0 (desde el ISP)**

| Línea | Acción | Origen | Destino | Motivo |
| --- | --- | --- | --- | --- |
| 10 | Denegar (log) | 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 127.0.0.0/8 | any | Anti-spoofing: rangos privados no pueden venir de Internet |
| 20 | Denegar (log) | 203.0.113.16/29 | any | Anti-spoofing: nadie de afuera puede usar el prefijo propio |
| 30 | Denegar (log) | any | 203.0.113.2 y 203.0.113.17, TCP 22 y 23 | Nadie gestiona el router de borde desde Internet |
| 40 | Permitir | any | any | El FortiGate decide el resto |

En IPv6 se deniega como origen el propio 2001:db8:105::/48 y fc00::/7 (ULA), y se bloquea SSH/Telnet hacia las direcciones del router.

**ACL vs. política del firewall**

| Aspecto | ACL de router | Política del FortiGate |
| --- | --- | --- |
| Estado | Sin estado: cada paquete se evalúa solo y la respuesta necesita su propia regla | Con estado: la respuesta pertenece a la sesión ya permitida |
| Paquete forjado | Un segmento con ACK pasa `established` aunque no exista la conexión | Se descarta: no pertenece a ninguna sesión |
| Dónde se aplica | Una interfaz y un sentido | Par de interfaces o zonas de entrada y salida |
| Criterios | IP, protocolo y puerto | Objetos, servicios, usuarios y, si se quiere, aplicación |
| NAT | No | Sí (VIP y SNAT) |
| Evidencia | Contadores por línea | Log por sesión con ID de política, además de contadores |
| Uso en este diseño | Anti-spoofing, segmentación entre VLAN y gestión de los routers | Control entre zonas y publicación del servicio |

## Servicio DNS/HTTP

SRV-DMZ es servidor autoritativo de `g5.eif101o.test` y sirve la página web, todo sobre IPv4 e IPv6. Usa dos vistas DNS: afuera, `www` resuelve al VIP público; adentro, a la IP privada real.

**Servicios en SRV-DMZ**

| Servicio | Software | Escucha en | Puertos |
| --- | --- | --- | --- |
| DNS autoritativo | bind9 | 10.50.1.34 y 2001:db8:105:30::10 | 53 UDP y TCP |
| Web | nginx | 10.50.1.34 y 2001:db8:105:30::10 | 80 TCP |
| Administración | OpenSSH | 10.50.1.34 y 2001:db8:105:30::10 | 22 TCP (solo lo permite la política 2) |

El servidor es **solo autoritativo**, con la recursión desactivada. Así no se convierte en un resolver abierto hacia Internet, y en el laboratorio los clientes lo consultan directamente.

**Vistas DNS (split horizon)**

| Vista | Clientes que la usan | Por qué |
| --- | --- | --- |
| interna | 10.50.0.0/16 y 2001:db8:105::/48, **excepto** 2001:db8:105:ff01::/64 | Desde la LAN, el VIP no es alcanzable sin hairpin NAT. Se responde la IP real |
| externa | todo lo demás | Desde afuera solo existe el VIP |

Funciona porque el VIP traduce el destino pero conserva el origen. El servidor ve la IP real del cliente externo y elige la vista correcta.

La excepción importa porque la WAN pública (2001:db8:105:ff01::/64) sale del mismo /48 que la LAN, pero está del lado de afuera del firewall. Sin excluirla, una consulta desde R-EDGE recibiría las direcciones privadas. En bind9 se escribe como un `acl` con la negación primero: `!2001:db8:105:ff01::/64; 10.50.0.0/16; 2001:db8:105::/48;`.

**Registros de la zona g5.eif101o.test**

| Nombre | Tipo | Vista externa | Vista interna |
| --- | --- | --- | --- |
| g5.eif101o.test. | SOA | ns1.g5.eif101o.test., serial con fecha (2026101801) | igual |
| g5.eif101o.test. | NS | ns1.g5.eif101o.test. | igual |
| ns1 | A | 203.0.113.20 | 10.50.1.34 |
| ns1 | AAAA | 2001:db8:105:30::10 | 2001:db8:105:30::10 |
| www | A | 203.0.113.20 | 10.50.1.34 |
| www | AAAA | 2001:db8:105:30::10 | 2001:db8:105:30::10 |
| v4 | A | 203.0.113.20 | 10.50.1.34 |
| v6 | AAAA | 2001:db8:105:30::10 | 2001:db8:105:30::10 |

El AAAA es igual en ambas vistas porque en IPv6 no hay traducción: la dirección global del servidor es la misma desde cualquier lado. No se implementan zonas inversas porque el enunciado no las pide.

**Por qué `v4` y `v6`.** Como `www` tiene A y AAAA, el navegador elige solo la familia y casi siempre prefiere IPv6 (Happy Eyeballs). Con `v4.g5.eif101o.test` (solo A) y `v6.g5.eif101o.test` (solo AAAA), la defensa muestra cada familia por nombre en el navegador, sin escribir direcciones IP. Con `dig` y `curl -4`/`-6` se sigue usando `www`. nginx responde a los tres nombres (`server_name`).

**Página web (index.html)**

- **Identifica:** el número de grupo, los integrantes, "Caso E - DMZ corporativa protegida" y el FQDN www.g5.eif101o.test.
- **IP del cliente:** nginx imprime la IP del cliente (variable `$remote_addr`, con SSI o un `return` aparte). Abriendo `v4` y `v6`, la misma página muestra una dirección IPv4 y luego una IPv6. Eso sirve como evidencia de dual-stack y prueba que el VIP no oculta el origen.

## Matriz de pruebas

Son 28 pruebas en cuatro grupos:

- Las 7 mínimas del enunciado (P).
- Las 17 específicas del caso E (E).
- Las 2 de enrutamiento (R).
- Dos fallas controladas (F).

Una pieza está terminada cuando sus pruebas dan el resultado esperado en la topología integrada. La evidencia se guarda como `<ID>_<descripcion>.png`.

Antes de armar la maqueta, la matriz completa se corre en el simulador lógico (`simulacion/sim_caso_e.py`), que reproduce las tablas de este documento. El simulador también verifica el plan B. No reemplaza las pruebas en GNS3, porque no modela capa 2 ni las particularidades de las imágenes.

**Pruebas mínimas del enunciado**

| ID | Prueba | Desde | Hacia | Resultado esperado | Evidencia |
| --- | --- | --- | --- | --- | --- |
| P01 | Resolución A | PC-EXT | www.g5.eif101o.test | 203.0.113.20 | Salida de la consulta |
| P02 | Resolución AAAA | PC-EXT | www.g5.eif101o.test | 2001:db8:105:30::10 | Salida de la consulta |
| P03 | Consulta DNS por IPv4 | PC-EXT | servidor en 203.0.113.20 | Respuesta autoritativa recibida por IPv4 | Consulta + log de la política 1 |
| P04 | Consulta DNS por IPv6 | PC-EXT | servidor en 2001:db8:105:30::10 | Respuesta autoritativa recibida por IPv6 | Consulta + log de la política 1 |
| P05 | HTTP por IPv4 con nombre | PC-EXT (`curl -4` a www) y PC-EXT-WEB (navegador a v4.g5.eif101o.test) | servidor por el VIP | Página del grupo, HTTP 200, muestra una IP cliente IPv4 | Salida + captura del navegador |
| P06 | HTTP por IPv6 con nombre | PC-EXT (`curl -6` a www) y PC-EXT-WEB (navegador a v6.g5.eif101o.test) | 2001:db8:105:30::10 | Página del grupo, HTTP 200, muestra una IP cliente IPv6 | Salida + captura del navegador |
| P07 | Política permitida y denegada | - | - | Se cumple con P05 y E01 | Logs con ID de política |

**Pruebas específicas del caso E**

| ID | Prueba | Desde | Hacia | Resultado esperado | Evidencia |
| --- | --- | --- | --- | --- | --- |
| E01 | Externo hacia la LAN por IPv6 | PC-EXT | IPv6 global de PC-USER | Bloqueado. La ruta existe pero la política 5 lo deniega | Log de la política 5 |
| E02 | Externo hacia la LAN por IPv4 | PC-EXT | 10.50.0.10 | Sin ruta: 10.50/16 no existe fuera del NAT | Traceroute que muere en R-ISP |
| E02b | Lo mismo, con una ruta filtrada | PC-EXT, tras agregar temporalmente 10.50.0.0/16 en R-ISP (vía R-EDGE) y en R-EDGE (vía 203.0.113.18) | 10.50.0.10 | El paquete llega al FortiGate y la política 5 lo deniega. La LAN no depende solo del NAT | Log de la política 5. Después se quitan las dos rutas |
| E03 | SSH externo al servidor | PC-EXT | VIP, puerto 22 | Bloqueado: no es un servicio publicado | Log de la denegación implícita |
| E04 | Admin por SSH al servidor | PC-ADMIN | SRV-DMZ, puerto 22 | Conecta | Sesión + log de la política 2 |
| E05 | Usuario por SSH al servidor | PC-USER | SRV-DMZ, puerto 22 | Bloqueado | Log de la denegación implícita |
| E06 | Usuario consume DNS y HTTP | PC-USER | www.g5.eif101o.test | A = 10.50.1.34 (vista interna), AAAA y página cargan | Salida + log de la política 3 |
| E07 | Usuarios hacia Admin | PC-USER | PC-ADMIN | Bloqueado | Contador de ACL-SEG-USUARIOS, línea 30 |
| E08 | Admin hacia Usuarios (ACL sin estado) | PC-ADMIN | PC-USER (ping) | Responde gracias a la línea 10 | Contador de la línea 10 |
| E09 | DMZ hacia la LAN | SRV-DMZ | PC-USER | Bloqueado | Log de la política 6 |
| E10 | Origen falsificado en el borde | R-ISP, con una loopback temporal 10.99.99.99 | VIP | Descartado en R-EDGE | Contador de ACL-BORDE-IN, línea 10 |
| E11 | Gestión del FortiGate desde la WAN | PC-EXT | 203.0.113.18 por HTTPS | Rechazado: port1 no permite HTTPS | Intento fallido + log local-in |
| E12 | Gestión de R-LAN | PC-USER y PC-ADMIN | R-LAN (10.50.0.1 y 2001:db8:105:ff00::2), SSH | Bloqueado desde PC-USER, conecta desde PC-ADMIN | Contador de ACL-VTY-ADMIN, línea 20 + sesión de PC-ADMIN |
| E13 | Gestión del FortiGate desde Usuarios | PC-USER y PC-ADMIN | 10.50.1.49 por HTTPS | Sin respuesta para PC-USER (trusted hosts), GUI para PC-ADMIN | Intento fallido + log local-in + captura de la GUI |
| E14 | El servidor inicia tráfico a Internet | SRV-DMZ | 198.51.100.10 | Bloqueado: no hay política DMZ → WAN. Un servidor comprometido no puede sacar datos | Log de la denegación implícita |
| E15 | Destino interno inexistente | PC-USER | 10.50.99.9 y 2001:db8:105:99::9 | Descartado en el FortiGate por la blackhole. No sale a Internet ni rebota con R-EDGE | Ruta en la tabla del FGT + ping fallido sin entrada de la política 4 |
| E16 | Logs fuera del FortiGate | FGT-01 y R-LAN | PC-ADMIN, UDP 514 | Las entradas de E01, E07 y E12 aparecen en el syslog de PC-ADMIN | Archivo de syslog de PC-ADMIN |

**Enrutamiento**

| ID | Prueba | Resultado esperado |
| --- | --- | --- |
| R01 | Vecinos OSPFv2 y OSPFv3 entre FGT-01 y R-LAN | Estado FULL en ambos protocolos; en OSPFv3 el vecino se ve por su link-local |
| R02 | Tablas de rutas de los cuatro equipos | Coinciden con la sección Enrutamiento, blackholes incluidas |

**Fallas y cambios controlados**

| ID | Acción | Resultado esperado | Recuperación |
| --- | --- | --- | --- |
| F01 | Desactivar la política 1 | P01 a P06 fallan desde afuera y el log muestra la denegación implícita | Reactivarla: vuelven a pasar sin otro cambio |
| F02 | Apagar R-LAN Gi0/0 | La vecindad OSPF cae: al instante en R-LAN, al vencer el dead interval en el FGT. La LAN pierde la ruta por defecto y la DMZ. Desde afuera la publicación sigue funcionando | Levantar la interfaz: la vecindad y las rutas se reconstruyen |

## Repositorio de configuraciones

Cada equipo y cada servicio tiene un archivo de texto en el repositorio, y ese archivo manda. Un cambio se escribe primero ahí y después se aplica al equipo, nunca al revés.

El repositorio es `IzukuCR/redes-caso-e` (privado). El flujo de trabajo completo está en `CONTRIBUTING.md`.

```text
redes-caso-e/
├── README.md              qué es el repo, versión vigente de la maqueta y cómo empezar
├── CONTRIBUTING.md        flujo de ramas, PR, revisión y publicación de versiones
├── docs/
│   ├── especificacion.md  este documento
│   ├── topologia.svg      diagrama de la topología (el que muestra el README)
│   ├── topologia.html     el mismo diagrama con leyenda y tabla de segmentos
│   └── enunciado-v3.pdf   instrucciones del profesor
├── configs/
│   ├── R-ISP.txt
│   ├── R-EDGE.txt
│   ├── R-LAN.txt
│   ├── FGT-01.conf
│   └── switches.md        puertos y VLAN de SW-LAN y SW-DMZ
├── hosts/
│   └── hosts.md           IP, gateway y DNS de cada host, y su /etc/network/interfaces
├── servicios/
│   ├── dns/               named.conf y un archivo de zona por vista
│   └── web/               index.html y configuración de nginx
├── simulacion/
│   └── sim_caso_e.py      simulador lógico: corre la matriz y el plan B sobre estas tablas
├── pruebas/
│   ├── matriz.md          copia de trabajo de la matriz, con estado por prueba
│   └── evidencias/        capturas con nombre <ID>_<descripcion>.png
├── informe/               borradores de las secciones del PDF
├── bitacora.md            incidencias: síntoma, diagnóstico, causa, solución
├── CHANGELOG.md           una línea por versión publicada de la maqueta
└── .github/               plantilla de PR, plantilla de issue y la Action del simulador
```

**Reglas de trabajo**

- **Un archivo por equipo.** Los bloques van en el mismo orden que este documento: interfaces, enrutamiento, seguridad. Así cualquiera encuentra lo que busca.
- **Mensajes de commit.** Nombran el equipo y la prueba que habilitan (por ejemplo, "R-LAN: ACL-SEG-USUARIOS, habilita E07").
- **Exportaciones de GNS3.** Los proyectos exportados no van al repositorio por su tamaño. Van a la carpeta compartida de Drive con el nombre `casoE_vN`, y el CHANGELOG registra qué cambió.
- **Una sola persona integra.** Aplica los archivos en la maqueta oficial y publica cada versión nueva.
- **Simulador al día.** Si cambia una tabla de este documento (direcciones, rutas, políticas, ACL o DNS), se actualiza también `sim_caso_e.py` y se vuelve a correr antes de tocar la maqueta.
- **Anexos del informe.** Los archivos de `configs/` y `servicios/` son los anexos de configuración completa. No hay que reconstruirlos al final.

## Decisiones pendientes

Hay doce puntos por cerrar antes de congelar la maqueta. Los tres primeros pueden cambiar el diseño; los demás solo ajustan detalles.

- [ ] Confirmar con el profesor el bloque del grupo (10.50.0.0/16, 2001:db8:105::/48, g5) y el número de grupo para nombrar el PDF.
- [ ] Revisar en la OVA la versión de FortiOS y su licencia. Si es la de prueba (máximo 3 políticas), se aplica el plan B de la sección FortiGate.
- [ ] Con esa misma versión, confirmar dos funciones. La primera: políticas con IPv4 e IPv6 juntas (nativas desde 7.0; en 6.4 hace falta el modo consolidado, y si no, se duplican). La segunda: `default-information-originate` en OSPFv3. Si no existe, R-LAN lleva una estática ::/0 hacia la link-local del FGT.
- [ ] Confirmar la imagen de los routers (IOSv u otra) y ajustar los nombres de interfaz del cableado.
- [ ] Elegir la imagen de PC-ADMIN: una con terminal, navegador y un servidor syslog (rsyslog o syslog-ng). Si no hay una que reúna todo, el FortiGate se administra por la consola de GNS3 y el syslog va solo al disco local.
- [ ] Verificar que los contenedores Docker tengan IPv6 habilitado (`disable_ipv6=0`) y, en PC-USER, que acepten RA (`accept_ra=1`) para que funcione SLAAC.
- [ ] Anotar la dirección SLAAC real de PC-USER (`ip -6 addr`) antes de E01. Puede ser EUI-64 o aleatoria según la imagen.
- [ ] Confirmar que la plantilla del FortiGate tenga el disco de logs conectado y que la VM de GNS3 tenga RAM suficiente (unos 4–5 GB para FGT, 3 IOSv y 6 contenedores).
- [ ] Vistas DNS (propuesta actual) o hairpin NAT en el FortiGate para que la LAN llegue al servicio por nombre.
- [ ] Enlaces punto a punto IPv6 en /64 (propuesta actual, más simple) o en /127 (RFC 6164).
- [ ] Cómo obtiene PC-USER el DNS en IPv6: manual, RDNSS en el RA o DHCPv6 stateless, según lo que soporte la imagen de R-LAN. Mientras tanto, el DNS por IPv4 ya resuelve los AAAA.
- [ ] Mantener o quitar la salida a Internet de la LAN (política 4). El caso E no la exige. Si se quita, las blackhole dejan de ser necesarias.
