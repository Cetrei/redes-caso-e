# Automatización de la maqueta

`gns3ctl.py` arma la maqueta en GNS3 desde los archivos de `topologia/` y `configs/`. Se edita el archivo y se aplica.

## Requisitos

La VM de GNS3 arrancada (`gns3vm/start-gns3vm.sh`) y `uv`, o Python 3.10+ con `pyyaml` y `paramiko`.

## Uso

Desde esta carpeta:

```
./gns3ctl.py validar        # revisa topologia/ sin tocar GNS3
./gns3ctl.py construir      # crea proyecto, equipos, configs y cables
./gns3ctl.py iniciar        # enciende los nodos (el FortiGate tarda 2 a 3 minutos)
./gns3ctl.py fortigate      # pega la config del FortiGate (y avisa de cada línea que FortiOS rechace)
./gns3ctl.py licenciar      # activa la licencia de evaluación del FortiGate
./gns3ctl.py posiciones     # aplica x e y de cada equipo y dibuja zonas y notas en el lienzo
./gns3ctl.py --help
```

## Cambiar la maqueta

- Un equipo es un archivo en `topologia/nodos/<EQUIPO>.yml`. Su posición es el `x` e `y` del archivo.
- Los cables van en `topologia/enlaces/`, un archivo por segmento.
- La config de cada equipo está en `configs/`.
- Para guardar en el repo lo que moviste en GNS3: `./gns3ctl.py posiciones --guardar`.
- `construir` solo agrega: lo que quites de los archivos se borra a mano en GNS3.

## Zonas y notas del lienzo

`posiciones` también dibuja lo que está en `topologia/zonas.yml` y `topologia/notas.yml`. Se repite sin duplicar: crea lo nuevo, actualiza lo que cambió y retira lo que quitaste del archivo. Si la GUI ya estaba abierta, los dibujos aparecen solos; si no, cierra y reabre el proyecto.

- Una zona es una caja con título: `{nombre, x, y, ancho, alto, tono, lineas}`. `nombre` no se repite y `lineas` es una lista opcional de textos debajo del título.
- Una nota es un texto suelto: `{texto, x, y}`. Con `ancho` y `alto` juntos se dibuja dentro de una caja. Admite `tono`, `tam` (tamaño de letra, 10 por defecto) y `negrita`. `\n` separa renglones.
- Los tonos son `neutro`, `gris`, `ambar`, `verde`, `violeta`, `rojo` y `exito`.
- Las notas se identifican por su orden en el archivo: al insertar una en medio, las siguientes se redibujan.

## Plan A y plan B del FortiGate

`fortigate` pega `configs/FGT-01-planB.conf` (plan B, tres políticas), porque la licencia de evaluación solo admite tres (`plan_b: true` en `topologia/proyecto.yml`). Con `plan_b: false` pega `configs/FGT-01.conf` (plan A, seis políticas) y, si FortiOS rechaza alguna, cae al plan B y lo avisa. El plan B usa central NAT para que una sola política cubra a los externos (por el VIP) y a los usuarios (por la IP real).

## Licenciar el FortiGate

1. `cp .env.example .env`, llena tu cuenta de FortiCloud y `chmod 600 .env`. El `.env` no se sube al repo.
2. Con la maqueta encendida: `./gns3ctl.py licenciar`.

La licencia queda ligada a esa instancia: no corras `destruir` después.

## Pruebas

```
python3 -m unittest discover -s tests -t .
```
