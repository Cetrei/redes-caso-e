# Automatización de la maqueta

`gns3ctl.py` arma la maqueta en GNS3 a partir de archivos de texto, sin tocar la interfaz gráfica. Sigue la regla del repo: **el archivo manda**. Para cambiar la maqueta se edita un archivo de `topologia/` (o una config de `configs/`) y se aplica; nunca al revés.

## Uso

Con la VM de GNS3 arrancada (`gns3vm/start-gns3vm.sh`), desde esta carpeta:

```
./gns3ctl.py validar        # revisa topologia/ sin tocar GNS3
./gns3ctl.py construir      # crea proyecto, equipos, configs y cables (se puede repetir)
./gns3ctl.py iniciar        # enciende los nodos (el FortiGate tarda 2 a 3 minutos)
./gns3ctl.py fortigate      # pega la config del FortiGate por su consola
./gns3ctl.py posiciones     # aplica x,y de cada equipo al lienzo
./gns3ctl.py --help         # lista completa
```

Necesita `uv` (instala solo pyyaml y paramiko) o un Python 3.10+ con esos dos paquetes.

## Estructura

```
automatizacion/
├── gns3ctl.py              entrada: solo arma los subcomandos
├── topologia/              LOS DATOS (lo que cambia el grupo)
│   ├── proyecto.yml        servidor, plantillas, tipos, FortiGate, imagenes Docker
│   ├── nodos/<EQUIPO>.yml  un archivo por equipo: plantilla, x, y, config o red
│   └── enlaces/<segmento>.yml   los cables, un archivo por segmento
└── maqueta/                EL MOTOR (casi nunca se toca)
    ├── tipos/              un modulo por tipo de nodo: dynamips, qemu, docker, switch
    └── comandos/           un modulo por subcomando
```

Regla de oro: **agregar, quitar o mover un equipo es tocar archivos de `topologia/`, no código**. El nombre del archivo es el nombre del equipo en GNS3.

## Dónde queda cada cosa en el lienzo

La posición de un equipo es el `x` e `y` de su archivo en `topologia/nodos/`. Son píxeles del lienzo de GNS3: el `(0, 0)` es el centro, `x` crece hacia la derecha e `y` hacia abajo. Los cables se dibujan solos como líneas rectas entre los dos equipos.

La maqueta usa filas separadas por 200 px: arriba (`y: -300`) el camino de afuera hacia adentro (R-ISP, R-EDGE, FGT-01, R-LAN, de izquierda a derecha); los clientes externos a la izquierda; los switches en `y: -100` y los hosts en `y: 100`. Usá múltiplos de 100 para que todo quede alineado.

Dos formas de acomodar:
- Editás `x` e `y` en el archivo y corrés `./gns3ctl.py posiciones` (repo → GNS3).
- Arrastrás los equipos en la interfaz de GNS3 y corrés `./gns3ctl.py posiciones --guardar` (GNS3 → repo). Después hacé commit solo de los archivos que moviste.

## Recetas

**Agregar un equipo** (por ejemplo un segundo cliente en la DMZ):
1. Copiá `topologia/nodos/PC-USER.yml` como `topologia/nodos/PC-DMZ2.yml` y cambiá `x`, `y` y la plantilla si hace falta.
2. Si es un contenedor, agregá su bloque `### PC-DMZ2` en `hosts/hosts.md`. Si es un router, su config va en `configs/` y el archivo del nodo la nombra con `config:`.
3. Agregá su cable en el archivo de `topologia/enlaces/` que corresponda (`[SW-DMZ, p2, PC-DMZ2, eth0]`).
4. `./gns3ctl.py validar`, después `construir` e `iniciar`.

**Quitar un equipo:** borrá su archivo de `nodos/` y sus líneas de `enlaces/`. `construir` solo agrega, así que el nodo viejo hay que borrarlo a mano en GNS3.

**Cambiar un cable:** editá la línea en `enlaces/`. El cable viejo también se borra a mano en GNS3.

**Cambiar la config de un equipo:** se edita su archivo de `configs/`, como siempre, y `construir` (routers) o `fortigate` la aplican.

**Un tipo de equipo nuevo** (por ejemplo VPCS): creá `maqueta/tipos/vpcs.py` con `puerto()` y `preparar()` (mirá `qemu.py`, el más corto), registralo en `maqueta/tipos/__init__.py` y agregá su alias en `proyecto.yml` (`plantillas` y `tipos`).

**Un subcomando nuevo:** creá su módulo en `maqueta/comandos/` con un diccionario `COMANDOS` y agregalo a `MODULOS` en `comandos/__init__.py`.

## Para que los merges no sean un caos

- Un equipo, un archivo. Dos personas que tocan equipos distintos nunca chocan.
- Los cables van por segmento (`externa`, `firewall`, `dmz`, `lan`). Si agregás una zona nueva, creá su propio archivo en `enlaces/`.
- `proyecto.yml` solo cambia cuando hay un alias de plantilla nuevo. Si dos PR agregan una línea ahí, el conflicto es de una línea: quedate con las dos.
- Corré `./gns3ctl.py validar` antes de abrir el PR: detecta plantillas inexistentes, puertos repetidos o mal escritos, equipos sin cable y archivos de config que no existen. `construir` lo corre solo.
- No muevas equipos ajenos sin motivo: con `posiciones --guardar`, revisá `git status` y commiteá solo los tuyos.
