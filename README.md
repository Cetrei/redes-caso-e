# Redes Avanzadas I — Caso E: DMZ corporativa protegida

Proyecto del curso EIF 101O (UNA): diseño e implementación en GNS3 de una red empresarial que publica DNS y HTTP desde una DMZ, sin exponer la LAN interna. Grupo **Los Arepísticos**.

## Estado

| Elemento | Valor |
| --- | --- |
| Versión vigente de la maqueta | — (todavía no se publica `casoE_v1`) |
| Entrega Parte I (PDF) | 31 de octubre |
| Defensa Parte II | 4 de noviembre |

## Qué hay en el repo

El repo guarda **solo texto**. La maqueta de GNS3 no se versiona acá: tiene discos binarios e imágenes con licencia de Cisco y Fortinet que no se pueden distribuir.

| Carpeta | Contenido |
| --- | --- |
| `docs/` | [Especificación de la topología](docs/especificacion.md) (la fuente de la verdad del diseño) y el enunciado del profesor |
| `configs/` | Configuración de cada router, del FortiGate y de los switches |
| `hosts/` | Direccionamiento y red de cada contenedor Docker |
| `servicios/` | bind9 (DNS) y nginx (web) de SRV-DMZ |
| `simulacion/` | Simulador lógico que corre la matriz de pruebas sobre las tablas del documento |
| `pruebas/` | Matriz de pruebas con su estado y las capturas de evidencia |
| `informe/` | Borradores de las secciones del PDF |
| `bitacora.md` | Incidencias reales (el informe pide al menos dos) |
| `CHANGELOG.md` | Una línea por versión publicada de la maqueta |

## Cómo empezar

1. Cloná el repo **fuera de OneDrive**, por ejemplo en `C:\repos`. OneDrive corrompe la carpeta `.git`.
   ```
   git clone https://github.com/IzukuCR/redes-caso-e.git C:\repos\redes-caso-e
   ```
2. Descargá la última `casoE_vN.gns3project` de la carpeta compartida de Drive e importala en GNS3 (Archivo → Importar proyecto). Las imágenes las pone cada uno desde la OVA.
3. Corré el simulador para ver que todo pasa:
   ```
   python simulacion/sim_caso_e.py
   ```
4. Leé [CONTRIBUTING.md](CONTRIBUTING.md) antes de tu primer cambio.
