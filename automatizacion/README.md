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
./gns3ctl.py fortigate      # pega la config del FortiGate
./gns3ctl.py licenciar      # activa la licencia de evaluación del FortiGate
./gns3ctl.py posiciones     # aplica x e y de cada equipo al lienzo
./gns3ctl.py --help
```

## Cambiar la maqueta

- Un equipo es un archivo en `topologia/nodos/<EQUIPO>.yml`. Su posición es el `x` e `y` del archivo.
- Los cables van en `topologia/enlaces/`, un archivo por segmento.
- La config de cada equipo está en `configs/`.
- Para guardar en el repo lo que moviste en GNS3: `./gns3ctl.py posiciones --guardar`.
- `construir` solo agrega: lo que quites de los archivos se borra a mano en GNS3.

## Licenciar el FortiGate

1. `cp .env.example .env`, llena tu cuenta de FortiCloud y `chmod 600 .env`. El `.env` no se sube al repo.
2. Con la maqueta encendida: `./gns3ctl.py licenciar`.

La licencia queda ligada a esa instancia: no corras `destruir` después.

## Pruebas

```
python3 -m unittest discover -s tests -t .
```
