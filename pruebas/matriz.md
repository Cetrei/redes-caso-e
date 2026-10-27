# Matriz de pruebas: copia de trabajo

El detalle de cada prueba (desde, hacia y evidencia) está en la sección Matriz de pruebas de `docs/especificacion.md`. Aquí solo se lleva el estado en la maqueta.

**Estados:** Pendiente · En curso · OK · Falla. Una prueba queda **OK** cuando da el resultado esperado en la maqueta integrada y su captura está en `evidencias/`.

| ID | Prueba | Resultado esperado | Simulador | Maqueta | Responsable | Evidencia |
| --- | --- | --- | --- | --- | --- | --- |
| P01 | Resolución A desde PC-EXT | 203.0.113.20 | OK | OK | | maqueta-20261024-1734.txt |
| P02 | Resolución AAAA desde PC-EXT | 2001:db8:105:30::10 | OK | OK | | maqueta-20261024-1734.txt |
| P03 | Consulta DNS por IPv4 | Respuesta autoritativa + log política 1 | OK | OK | | maqueta-20261024-1734.txt |
| P04 | Consulta DNS por IPv6 | Respuesta autoritativa + log política 1 | OK | OK | | maqueta-20261024-1734.txt |
| P05 | HTTP IPv4 por nombre (www y v4) | HTTP 200, IP cliente IPv4 | OK | OK | | maqueta-20261024-1734.txt |
| P06 | HTTP IPv6 por nombre (www y v6) | HTTP 200, IP cliente IPv6 | OK | OK | | maqueta-20261024-1734.txt |
| P07 | Política permitida y denegada | P05 + E01 | OK | OK | | maqueta-20261024-1734.txt |
| E01 | Externo → LAN por IPv6 | Bloqueado por política 3 (DENY-A-LAN) | OK | OK | | maqueta-20261024-1734.txt |
| E02 | Externo → LAN por IPv4 | Sin ruta en R-ISP | OK | OK | | maqueta-20261024-1734.txt |
| E02b | Externo → LAN con ruta filtrada | Denegado en port1 | OK | OK | | extras-20261024-1813.txt |
| E03 | SSH externo al servidor | Denegación implícita | OK | OK | | maqueta-20261024-1734.txt |
| E04 | Admin SSH al servidor | Conecta, política 2 | OK | OK | | maqueta-20261024-1734.txt |
| E05 | Usuario SSH al servidor | Denegación implícita | OK | OK | | maqueta-20261024-1734.txt |
| E06 | Usuario consume DNS y HTTP | Vista interna, política 1 | OK | OK | | maqueta-20261024-1734.txt |
| E07 | Usuarios → Admin | ACL-SEG-USUARIOS línea 30 | OK | OK | | maqueta-20261024-1734.txt |
| E08 | Admin → Usuarios (ping) | Responde por la línea 10 | OK | OK | | maqueta-20261024-1734.txt |
| E09 | DMZ → LAN | Bloqueado por política 3 (DENY-A-LAN) | OK | OK | | maqueta-20261024-1734.txt |
| E10 | Origen falsificado en el borde | ACL-BORDE-IN línea 10 | OK | OK | | extras-20261024-1813.txt |
| E11 | Gestión del FGT desde la WAN | Rechazado + log local-in | OK | OK | | maqueta-20261024-1734.txt |
| E12 | Gestión de R-LAN | Bloqueado a Usuarios, OK a Admin | OK | OK | | maqueta-20261024-1734.txt |
| E13 | GUI del FGT desde Usuarios | Sin respuesta (trusted hosts) | OK | OK | | maqueta-20261024-1734.txt |
| E14 | Servidor → Internet | Denegación implícita | OK | OK | | maqueta-20261024-1734.txt |
| E15 | Destino interno inexistente | Descartado por blackhole | OK | OK | | maqueta-20261024-1734.txt |
| E16 | Logs fuera del FGT | Syslog en PC-ADMIN | OK | OK | | extras-20261024-1813.txt |
| R01 | Vecinos OSPFv2 y OSPFv3 | FULL en ambos | OK | OK | | maqueta-20261024-1734.txt |
| R02 | Tablas de rutas | Coinciden con el documento | OK | OK | | extras-20261024-1813.txt |
| F01 | Desactivar política 1 | Publicación cae y vuelve | OK | OK | | maqueta-20261024-1734.txt |
| F02 | Apagar R-LAN Gi0/0 (Gi1/0 en el c7200) | LAN pierde servicio, externo sigue | OK | OK | | maqueta-20261024-1734.txt |

Maqueta verificada con `pruebas/verificar_maqueta.py` en el plan B (el que corre: tres politicas y central NAT). Con el plan B cambian las politicas que registran: E01 y E09 las registra la politica 3 (DENY-A-LAN), E06 y las pruebas P03 a P06 la politica 1 (DNS-HTTP-A-DMZ) y E04 la politica 2. E03, E05 y E14 caen en la denegacion implicita (politica 0), tambien registrada. Las pruebas E02b, E10, E16 y R02 las corre `pruebas/verificar_extras.py` (rutas temporales, loopback de origen falsificado, receptor syslog con socat en PC-ADMIN y tablas de los cinco equipos). Con esto no queda ninguna prueba pendiente en la maqueta.
