# Redes Avanzadas I — Caso E: DMZ corporativa protegida

Proyecto del curso EIF 101O (UNA): diseño e implementación en GNS3 de una red empresarial que publica DNS y HTTP desde una DMZ, sin exponer la LAN interna. Grupo **Los Arepísticos**.

![Topología del Caso E: red externa, WAN pública, FortiGate, LAN interna y DMZ](docs/topologia.svg)

El FortiGate es el único punto de paso entre zonas: la política 1 publica DNS y HTTP hacia la DMZ y la política 5 bloquea el acceso externo a la LAN. La versión con leyenda y tabla de segmentos está en [docs/topologia.html](docs/topologia.html).

## Estado

| Elemento | Valor |
| --- | --- |
| Versión vigente de la maqueta | — (todavía no se publica `casoE_v1`) |
| Entrega Parte I (PDF) | 31 de octubre |
| Defensa Parte II | 4 de noviembre |

## Credenciales del laboratorio

Todos los equipos usan **`admin` / `admin`**.

| Equipo | Usuario | Contraseña | Acceso |
| --- | --- | --- | --- |
| R-ISP | — | `admin` (enable) | Solo consola de GNS3 |
| R-EDGE | — | `admin` (enable) | Solo consola de GNS3 |
| R-LAN | `admin` | `admin` (también enable) | Consola, o SSH desde la VLAN 20 |
| FGT-01 | `admin` | `admin` | Consola, o GUI/SSH desde la VLAN 20 (10.50.1.49) |

En la primera entrada, el FortiGate pide cambiar la contraseña. Si la versión no acepta `admin`, anoten acá cuál usaron para que todo el grupo use la misma.

## Qué hay en el repo

El repo guarda **solo texto**. La maqueta de GNS3 no se versiona acá: tiene discos binarios e imágenes con licencia de Cisco y Fortinet que no se pueden distribuir.

| Carpeta | Contenido |
| --- | --- |
| `docs/` | [Especificación de la topología](docs/especificacion.md) (la fuente de la verdad del diseño), el diagrama de la topología (SVG y HTML) y el enunciado del profesor |
| `configs/` | Configuración de cada router, del FortiGate y de los switches |
| `hosts/` | Direccionamiento y red de cada contenedor Docker |
| `servicios/` | bind9 (DNS) y nginx (web) de SRV-DMZ |
| `simulacion/` | Simulador lógico que corre la matriz de pruebas sobre las tablas del documento |
| `pruebas/` | Matriz de pruebas con su estado y las capturas de evidencia |
| `informe/` | Borradores de las secciones del PDF |
| `bitacora.md` | Incidencias reales (el informe pide al menos dos) |
| `CHANGELOG.md` | Una línea por versión publicada de la maqueta |
