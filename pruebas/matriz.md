# Matriz de pruebas — copia de trabajo

El detalle de cada prueba (desde, hacia y evidencia) está en la sección Matriz de pruebas de `docs/especificacion.md`. Acá solo se lleva el estado en la maqueta.

**Estados:** Pendiente · En curso · OK · Falla. Una prueba queda **OK** cuando da el resultado esperado en la maqueta integrada y su captura está en `evidencias/`.

| ID | Prueba | Resultado esperado | Simulador | Maqueta | Responsable | Evidencia |
| --- | --- | --- | --- | --- | --- | --- |
| P01 | Resolución A desde PC-EXT | 203.0.113.20 | OK | Pendiente | | |
| P02 | Resolución AAAA desde PC-EXT | 2001:db8:105:30::10 | OK | Pendiente | | |
| P03 | Consulta DNS por IPv4 | Respuesta autoritativa + log política 1 | OK | Pendiente | | |
| P04 | Consulta DNS por IPv6 | Respuesta autoritativa + log política 1 | OK | Pendiente | | |
| P05 | HTTP IPv4 por nombre (www y v4) | HTTP 200, IP cliente IPv4 | OK | Pendiente | | |
| P06 | HTTP IPv6 por nombre (www y v6) | HTTP 200, IP cliente IPv6 | OK | Pendiente | | |
| P07 | Política permitida y denegada | P05 + E01 | OK | Pendiente | | |
| E01 | Externo → LAN por IPv6 | Bloqueado por política 5 | OK | Pendiente | | |
| E02 | Externo → LAN por IPv4 | Sin ruta en R-ISP | OK | Pendiente | | |
| E02b | Externo → LAN con ruta filtrada | Bloqueado por política 5 | OK | Pendiente | | |
| E03 | SSH externo al servidor | Denegación implícita | OK | Pendiente | | |
| E04 | Admin SSH al servidor | Conecta, política 2 | OK | Pendiente | | |
| E05 | Usuario SSH al servidor | Denegación implícita | OK | Pendiente | | |
| E06 | Usuario consume DNS y HTTP | Vista interna, política 3 | OK | Pendiente | | |
| E07 | Usuarios → Admin | ACL-SEG-USUARIOS línea 30 | OK | Pendiente | | |
| E08 | Admin → Usuarios (ping) | Responde por la línea 10 | OK | Pendiente | | |
| E09 | DMZ → LAN | Bloqueado por política 6 | OK | Pendiente | | |
| E10 | Origen falsificado en el borde | ACL-BORDE-IN línea 10 | OK | Pendiente | | |
| E11 | Gestión del FGT desde la WAN | Rechazado + log local-in | OK | Pendiente | | |
| E12 | Gestión de R-LAN | Bloqueado a Usuarios, OK a Admin | OK | Pendiente | | |
| E13 | GUI del FGT desde Usuarios | Sin respuesta (trusted hosts) | OK | Pendiente | | |
| E14 | Servidor → Internet | Denegación implícita | OK | Pendiente | | |
| E15 | Destino interno inexistente | Descartado por blackhole | OK | Pendiente | | |
| E16 | Logs fuera del FGT | Syslog en PC-ADMIN | OK | Pendiente | | |
| R01 | Vecinos OSPFv2 y OSPFv3 | FULL en ambos | OK | Pendiente | | |
| R02 | Tablas de rutas | Coinciden con el documento | OK | Pendiente | | |
| F01 | Desactivar política 1 | Publicación cae y vuelve | OK | Pendiente | | |
| F02 | Apagar R-LAN Gi0/0 | LAN pierde servicio, externo sigue | OK | Pendiente | | |
