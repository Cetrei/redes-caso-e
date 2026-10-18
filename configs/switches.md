# Switches (Ethernet switch integrado de GNS3)

Se configuran desde GNS3 (clic derecho → Configure). Fuente: sección Cableado de `docs/especificacion.md`.

| Switch | Puerto | Modo | VLAN | Conecta a |
| --- | --- | --- | --- | --- |
| SW-LAN | 0 | dot1q (troncal) | 10 y 20 etiquetadas | R-LAN Gi0/1 |
| SW-LAN | 1 | access | 10 | PC-USER |
| SW-LAN | 2 | access | 20 | PC-ADMIN |
| SW-DMZ | 0 | access | 1 | FGT-01 port3 |
| SW-DMZ | 1 | access | 1 | SRV-DMZ |
