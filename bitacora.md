# Bitácora de incidencias

Una entrada por problema real encontrado durante el desarrollo. El informe pide al menos dos, con diagnóstico y solución.

## Plantilla

```
### INC-NN — Título corto
- Fecha:
- Quién:
- Equipo(s):
- Síntoma: qué se observó (comando y salida)
- Diagnóstico: qué se revisó y en qué orden
- Causa:
- Solución: qué se cambió (commit o PR)
- Prueba que lo confirma: ID de la matriz
```

## Incidencias

### INC-01 — Clientes Alpine sin red estática
- Fecha: 2026-10-21
- Quién: Cetrei
- Equipo(s): PC-EXT, PC-USER
- Síntoma: la consola solo mostraba `udhcpc: broadcasting discover` y `ip -br a` no devolvía nada; ningún comando respondía.
- Diagnóstico: `start_command` de la plantilla Alpine del servidor era `sh -c "udhcpc -i eth0 && bash"`, y `udhcpc` nunca obtiene lease porque la maqueta no tiene DHCP, así que el shell no llega a abrirse.
- Causa: la plantilla arranca esperando DHCP y nunca aplica `/etc/network/interfaces`.
- Solución: imagen propia `caso-e/cliente` (`servicios/cliente/Dockerfile`) que arranca en `/bin/sh`, con dig, curl y ssh. Se construye con `automatizacion/gns3ctl.py imagen`.
- Prueba que lo confirma: base de P01 a P06 y E01 a E09 (los clientes ya tienen su IP).

### INC-02 — PC-USER sin IPv4 por `inet6 auto`
- Fecha: 2026-10-21
- Quién: Cetrei
- Equipo(s): PC-USER
- Síntoma: `ip -br a` mostraba solo la dirección IPv6 SLAAC y `ip route` estaba vacío; `ifup -a` respondía `unknown method "auto"`.
- Diagnóstico: el archivo de red estaba escrito correctamente; el error salía del `ifup` de BusyBox.
- Causa: BusyBox no soporta `iface eth0 inet6 auto` y aborta todo el archivo, incluida la parte IPv4.
- Solución: se quitó el bloque `inet6` de PC-USER en `hosts/hosts.md`; la IPv6 llega sola por SLAAC.
- Prueba que lo confirma: E01 y E06 (PC-USER con IPv4 y SLAAC).
