# Cómo trabajar en el repo

## La regla principal

**El archivo del repo manda.** Un cambio se escribe primero en el archivo de texto y después se aplica al equipo, nunca al revés. Si alguien toca la maqueta sin pasar por el repo, el cambio se pierde en la próxima versión.

## Flujo de un cambio

1. **Tomá un issue** del tablero (cada prueba de la matriz tiene uno) y asignátelo.
2. **Creá una rama** desde `main` actualizado:
   ```
   git switch main
   git pull
   git switch -c feat/r-lan-acl-vty
   ```
   Prefijos: `feat/` (algo nuevo), `fix/` (corrección), `docs/` (documento o informe), `test/` (evidencias).
3. **Escribí el cambio** en el archivo que corresponde (`configs/`, `servicios/`, `docs/`…).
4. **Probalo en tu copia local de la maqueta**, pegando la configuración por la consola de GNS3.
5. **Si tocaste una tabla de `docs/especificacion.md`** (direcciones, rutas, políticas, ACL o DNS), actualizá también `simulacion/sim_caso_e.py` y corré:
   ```
   python simulacion/sim_caso_e.py
   ```
   Tiene que terminar sin fallas.
6. **Commit** con un mensaje que nombre el equipo y la prueba que habilita:
   ```
   git commit -m "R-LAN: ACL-VTY-ADMIN, habilita E12"
   ```
7. **Push y Pull Request** hacia `main`. Completá la plantilla y pedile la revisión a otro integrante.
8. **Otro integrante revisa y aprueba.** Nadie fusiona su propio PR.

## Por qué la revisión es obligatoria

En la defensa, el profesor le pregunta a cada integrante por separado sobre direccionamiento, routing y políticas, aunque se hayan repartido las tareas. Revisar los PR de los demás es la forma de entender lo que no hiciste vos. Revisá preguntándote: "¿podría explicar esto en la defensa?".

## Versiones de la maqueta

Una sola persona (el integrador) mantiene la maqueta oficial:

1. Aplica `main` en la maqueta oficial.
2. Corre las pruebas de la matriz que dependen del cambio.
3. Exporta el proyecto **sin imágenes** (Archivo → Exportar proyecto) como `casoE_vN.gns3project`.
4. Lo sube a la carpeta compartida de Drive.
5. Agrega una línea en `CHANGELOG.md` y actualiza la versión vigente en el `README.md`.

## Cómo sacar la configuración de cada equipo

| Equipo | Cómo |
| --- | --- |
| Routers IOSv | `show running-config` y copiar la salida al archivo de `configs/` |
| FortiGate | `show` en la CLI (solo lo que no es por defecto) o respaldo desde la GUI. Antes de commitear, borrá claves privadas y certificados |
| Contenedores Docker | La red se edita en GNS3 (clic derecho → Edit network configuration) y se copia a `hosts/hosts.md` |
| bind9 y nginx | Los archivos del volumen persistente de SRV-DMZ se copian a `servicios/` |

## Evidencias

- Las capturas van en `pruebas/evidencias/` con el nombre `<ID>_<descripcion>.png` (por ejemplo `E01_ext_a_lan_ipv6.png`).
- Cuando una prueba da el resultado esperado en la maqueta integrada, se marca como **OK** en `pruebas/matriz.md` y se cierra su issue.

## Incidencias

Todo problema real que les cueste más de unos minutos va a `bitacora.md`: síntoma, diagnóstico, causa y solución. El informe pide al menos dos, y en la defensa sirven como ejemplo de troubleshooting.

## Qué no se sube nunca

- Imágenes o discos (`.qcow2`, `.vmdk`, `.iso`, `.ova`, `.bin`) ni exportaciones de GNS3: el `.gitignore` ya los bloquea.
- Licencias de Fortinet o claves privadas.

Las credenciales de todos los equipos son las del laboratorio, `admin` / `admin`, y pueden quedar en los archivos de `configs/`.
