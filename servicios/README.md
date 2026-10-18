# Servicios de SRV-DMZ

Fuente: sección Servicio DNS/HTTP de `docs/especificacion.md`.

| Carpeta | Archivos esperados |
| --- | --- |
| `dns/` | `named.conf` (con las vistas `interna` y `externa`, recursión desactivada), `db.g5.eif101o.test.interna` y `db.g5.eif101o.test.externa` |
| `web/` | `index.html` (grupo, integrantes, "Caso E — DMZ corporativa protegida", FQDN e IP del cliente) y la configuración de nginx con `server_name` para `www`, `v4` y `v6` |

Cada vez que cambie la zona, se sube el serial (`AAAAMMDDNN`). Estos archivos son también el anexo del informe.
