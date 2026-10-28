# Automatización de la maqueta

`gns3ctl.py` arma la maqueta del Caso E en GNS3 desde los archivos de `topologia/` y `configs/`: crea el proyecto, los equipos y los cables, carga las configuraciones, pega la del FortiGate y activa su licencia de evaluación. Se edita el archivo y se aplica; repetir un subcomando no duplica nada.

Funciona igual en Windows 11, Linux y macOS: es Python y se corre con `uv`. Los pasos de VirtualBox están escritos para Windows; en Linux y macOS se hacen con la misma configuración de la VM.

## Requisitos

1. **VirtualBox 7** con la OVA del profesor importada (la VM de GNS3 2.2).
2. **Reenvío de puertos** de la VM, en Configuración, Red, Adaptador 1 (NAT), Avanzadas, Reenvío de puertos. Se agregan estas reglas con IP de host 127.0.0.1:

   | Nombre | Protocolo | Puerto del host | Puerto del invitado |
   | --- | --- | --- | --- |
   | api | TCP | 3080 | 80 |
   | ssh | TCP | 2222 | 22 |
   | consolas | TCP | 5000 a 5039 | 5000 a 5039 |
   | vnc | TCP | 5900 a 5919 | 5900 a 5919 |

   VirtualBox pide una regla por puerto. Para crear las 60 de las consolas y del VNC de una vez, en PowerShell (con la VM apagada y el nombre real de la VM en `$vm`):

   ```
   $vm = "GNS3 VM 101O"
   & "C:\Program Files\Oracle\VirtualBox\VBoxManage.exe" modifyvm $vm --natpf1 "api,tcp,127.0.0.1,3080,,80"
   & "C:\Program Files\Oracle\VirtualBox\VBoxManage.exe" modifyvm $vm --natpf1 "ssh,tcp,127.0.0.1,2222,,22"
   (5000..5039) + (5900..5919) | ForEach-Object { & "C:\Program Files\Oracle\VirtualBox\VBoxManage.exe" modifyvm $vm --natpf1 "con$_,tcp,127.0.0.1,$_,,$_" }
   ```

3. **Virtualización anidada** habilitada en la VM (el FortiGate corre dentro de ella con KVM): en Configuración, Sistema, Procesador, marcar Habilitar VT-x/AMD-V anidado, o `VBoxManage modifyvm $vm --nested-hw-virt on`. Asigna a la VM al menos 4 vCPU y 6 GB de RAM. Si el nodo del FortiGate se congela al iniciar, revisa que Hyper-V, Plataforma de máquina virtual y Aislamiento del núcleo (Integridad de memoria) estén desactivados en Windows, porque compiten con VirtualBox por la virtualización por hardware.
4. **uv**, que instala Python y las dependencias (pyyaml y paramiko) por su cuenta. En Windows, desde PowerShell:

   ```
   winget install --id astral-sh.uv -e
   ```

   En Linux y macOS: `curl -LsSf https://astral.sh/uv/install.sh | sh`. Cierra y abre la terminal para que reconozca el comando. Sin uv también sirve Python 3.10 o más reciente con `py -m pip install pyyaml paramiko`, y se corre con `py gns3ctl.py` en lugar de `uv run gns3ctl.py`.

Antes de empezar, enciende la VM en VirtualBox y espera a que `http://127.0.0.1:3080/v2/version` responda en el navegador.

## Uso

Todo se corre desde esta carpeta (`automatizacion`), en PowerShell o en cualquier terminal. Se antepone `uv run` en todos los sistemas, que es lo que Windows necesita y también funciona en Linux y macOS.

```
uv run gns3ctl.py validar        # revisa topologia/ sin tocar GNS3
uv run gns3ctl.py imagen         # solo la primera vez: construye las imágenes Docker en la VM (SRV-DMZ, cliente y webterm)
uv run gns3ctl.py construir      # crea proyecto, equipos, configs y cables
uv run gns3ctl.py iniciar        # enciende los nodos (el FortiGate tarda 2 a 3 minutos)
uv run gns3ctl.py fortigate      # pega la config del FortiGate y avisa de cada línea que FortiOS rechace
uv run gns3ctl.py licenciar      # activa la licencia de evaluación del FortiGate
uv run gns3ctl.py posiciones     # aplica x e y de cada equipo y dibuja zonas y notas en el lienzo
uv run gns3ctl.py estado         # lista nodos, estado y puerto de consola
uv run gns3ctl.py --help
```

### Todo en un paso

`todo` encadena los pasos habituales y espera al FortiGate antes de licenciar. Con la VM encendida:

```
uv run gns3ctl.py todo
```

Sin argumentos corre `construir`, `iniciar` y `licenciar`. También acepta los pasos que le indiques, por ejemplo `uv run gns3ctl.py todo construir iniciar fortigate`. Se niega a correr `destruir` y, antes de tocar nada, comprueba que el `.env` esté lleno si vas a licenciar.

## Consolas de los equipos con navegador

PC-ADMIN, PC-USER y PC-EXT-WEB corren Firefox sobre VNC (la imagen `caso-e/webterm` para los dos primeros). Su consola principal es gráfica: doble clic en el nodo abre el cliente VNC. El terminal está en la consola auxiliar, con clic derecho y Auxiliary console. `estado` muestra la auxiliar como `consola` y el puerto VNC aparte, y las pruebas de `pruebas/` entran por esa auxiliar.

Si GNS3 intenta abrir el terminal con `xterm` y falla, instala xterm o cambia el comando en Edit, Preferences, General, Console applications.

## Licenciar el FortiGate

Un FortiGate recién desplegado no trae una licencia de evaluación válida y no reenvía tráfico hasta activarla con una cuenta de FortiCloud (https://support.fortinet.com).

1. Copia la plantilla y llénala con tu cuenta:

   ```
   Copy-Item .env.example .env     # en Linux y macOS: cp .env.example .env
   notepad .env                     # o el editor que prefieras; se acepta UTF-8 con o sin BOM
   ```

   `FORTICLOUD_CORREO` es el correo con el que entras a esa página y `FORTICLOUD_CLAVE` es su clave, sin espacios ni signos de interrogación. El `.env` no se sube al repo.
2. Con la maqueta encendida: `uv run gns3ctl.py licenciar`. El subcomando entra al FortiGate, conecta un nodo NAT temporal a `port4`, activa la licencia, espera el reinicio y verifica que quede en estado Valid; luego retira el NAT.

La licencia queda ligada a esa instancia del FortiGate: no corras `destruir` después.

## Plan A y plan B del FortiGate

`fortigate` pega `configs/FGT-01-planB.conf` (plan B, tres políticas), porque la licencia de evaluación solo admite tres (`plan_b: true` en `topologia/proyecto.yml`). Con `plan_b: false` pega `configs/FGT-01.conf` (plan A, seis políticas) y, si FortiOS rechaza alguna, cae al plan B y lo avisa. El plan B usa central NAT para que una sola política cubra a los externos (por el VIP) y a los usuarios (por la IP real).

## Cambiar la maqueta

- Un equipo es un archivo en `topologia/nodos/<EQUIPO>.yml`. Su posición es el `x` e `y` del archivo.
- Los cables van en `topologia/enlaces/`, un archivo por segmento.
- La config de cada equipo está en `configs/`.
- Para guardar en el repo lo que moviste en GNS3: `uv run gns3ctl.py posiciones --guardar`.
- `construir` solo agrega: lo que quites de los archivos se borra a mano en GNS3.

## Zonas y notas del lienzo

`posiciones` también dibuja lo que está en `topologia/zonas.yml` y `topologia/notas.yml`. Se repite sin duplicar: crea lo nuevo, actualiza lo que cambió y retira lo que quitaste del archivo. Si la GUI ya estaba abierta, los dibujos aparecen solos; si no, cierra y reabre el proyecto.

- Una zona es una caja con título: `{nombre, x, y, ancho, alto, tono, lineas}`. `nombre` no se repite y `lineas` es una lista opcional de textos debajo del título.
- Una nota es un texto suelto: `{texto, x, y}`. Con `ancho` y `alto` juntos se dibuja dentro de una caja. Admite `tono`, `tam` (tamaño de letra, 10 por defecto) y `negrita`. `\n` separa renglones.
- Los tonos son `neutro`, `gris`, `ambar`, `verde`, `violeta`, `rojo` y `exito`.
- Las notas se identifican por su orden en el archivo: al insertar una en medio, las siguientes se redibujan.

## Pruebas

Del motor, sin GNS3:

```
uv run --with pyyaml --with paramiko python -m unittest discover -s tests -t .
```

De la maqueta en vivo, con todo encendido y licenciado (desde la raíz del repo):

```
uv run python pruebas/verificar_maqueta.py
uv run python pruebas/verificar_extras.py
```

Cada una guarda su salida en `pruebas/evidencias/`. La segunda tarda unos 6 minutos.
