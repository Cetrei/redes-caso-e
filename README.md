# Redes Avanzadas I - Caso E: DMZ corporativa protegida

Proyecto del curso EIF 101O (UNA): diseño e implementación en GNS3 de una red empresarial que publica DNS y HTTP desde una DMZ, sin exponer la LAN interna. Grupo 5.

![Topología del Caso E: red externa, WAN pública, FortiGate, LAN interna y DMZ](docs/topologia.svg)

El FortiGate es el único punto de paso entre zonas: la política 1 publica DNS y HTTP hacia la DMZ y la política 3 (DENY-A-LAN) bloquea el acceso externo a la LAN, en el plan B que corre la maqueta. La versión con leyenda y tabla de segmentos está en [docs/topologia.html](docs/topologia.html).

## Estado

| Elemento | Valor |
| --- | --- |
| Versión vigente de la maqueta | - (todavía no se publica `casoE_v1`) |
| Entrega Parte I (PDF) | 31 de octubre |
| Defensa Parte II | 4 de noviembre |

## Arranque rápido

La maqueta se arma sola desde los archivos del repo, en Windows 11, Linux o macOS. El detalle de cada paso está en [automatizacion/README.md](automatizacion/README.md); este es el camino corto.

1. Instala **VirtualBox 7**, importa la OVA del profesor y configura el reenvío de puertos y la virtualización anidada de la VM (el README de `automatizacion/` trae los comandos).
2. Instala **uv** y reabre la terminal. En Windows, desde PowerShell:

   ```
   winget install --id astral-sh.uv -e
   ```

   En Linux y macOS: `curl -LsSf https://astral.sh/uv/install.sh | sh`.
3. Clona el repo, entra a `automatizacion/` y copia la plantilla de credenciales de FortiCloud:

   ```
   cd automatizacion
   Copy-Item .env.example .env     # en Linux y macOS: cp .env.example .env
   notepad .env                    # o el editor que prefieras
   ```
4. Enciende la VM, espera a que `http://127.0.0.1:3080/v2/version` responda y corre todo en un paso:

   ```
   uv run gns3ctl.py todo
   ```

`todo` construye el proyecto, enciende los nodos, espera al FortiGate y activa su licencia de evaluación. Con pasos sueltos (`uv run gns3ctl.py todo fortigate`, `uv run gns3ctl.py validar`) repite solo lo que necesitas. Se niega a correr `destruir`, porque borrar el FortiGate hace perder su licencia.

## Qué hay de nuevo

| Novedad | Dónde |
| --- | --- |
| Script `gns3ctl.py` que arma la maqueta completa (equipos, cables, configs, posiciones, zonas del lienzo) desde archivos de texto | `automatizacion/` |
| Subcomando `todo`, que encadena construir, iniciar y licenciar en Windows, Linux y macOS | `automatizacion/` |
| Plan B del FortiGate con tres políticas y central NAT, porque la licencia de evaluación no admite más | `configs/FGT-01-planB.conf` |
| Pruebas en vivo sobre la maqueta (las 28 pruebas de la matriz en verde) con su evidencia | `pruebas/` |
| Informe de la Parte I en Word | `informe/Grupo_05_Proyecto_Parte_I.docx` |

Las credenciales de FortiCloud viven en `automatizacion/.env`, que no se sube al repo.

## Credenciales del laboratorio

Todos los equipos usan **`admin` / `admin`**.

| Equipo | Usuario | Contraseña | Acceso |
| --- | --- | --- | --- |
| R-ISP | - | `admin` (enable) | Solo consola de GNS3 |
| R-EDGE | - | `admin` (enable) | Solo consola de GNS3 |
| R-LAN | `admin` | `admin` (también enable) | Consola, o SSH desde la VLAN 20 |
| FGT-01 | `admin` | `admin` | Consola, o GUI/SSH desde la VLAN 20 (10.50.1.49) |

En la primera entrada, el FortiGate pide cambiar la contraseña. Si la versión no acepta `admin`, anoten aquí cuál usaron para que todo el grupo use la misma.

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
| `automatizacion/` | `gns3ctl.py`, la definición de la maqueta en `topologia/` y sus pruebas |
| `informe/` | Informe de la Parte I en Word (`.docx`) y sus figuras en `informe/fuente/figuras/` |
| `bitacora.md` | Incidencias reales (el informe pide al menos dos) |
| `CHANGELOG.md` | Una línea por versión publicada de la maqueta |
| `LICENSE` | Licencia MIT del texto del repo |

## Licencia

El código, las configuraciones y los documentos de este repo se publican bajo la licencia MIT ([LICENSE](LICENSE)). Las imágenes de Cisco y Fortinet y el software de terceros que usa la maqueta no se incluyen y siguen sus propias licencias.
