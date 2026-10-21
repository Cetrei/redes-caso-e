# Servicios de SRV-DMZ

Fuente: sección Servicio DNS/HTTP de `docs/especificacion.md`. SRV-DMZ es un contenedor Alpine con **bind9** (DNS autoritativo de `g5.eif101o.test`), **nginx** (la página del grupo) y **OpenSSH** (administración desde la VLAN 20).

| Archivo | Ruta en el servidor | Qué hace |
| --- | --- | --- |
| `dns/named.conf` | `/etc/bind/named.conf` | Vistas `interna` y `externa`, solo autoritativo (sin recursión), log de consultas |
| `dns/db.g5.eif101o.test.interna` | `/etc/bind/zonas/` | `www`, `ns1` y `v4` → 10.50.1.34; AAAA → 2001:db8:105:30::10 |
| `dns/db.g5.eif101o.test.externa` | `/etc/bind/zonas/` | `www`, `ns1` y `v4` → 203.0.113.20 (VIP); AAAA igual que adentro |
| `web/caso-e.conf` | `/etc/nginx/http.d/default.conf` | Sitio para `www`, `v4` y `v6`, en IPv4 e IPv6, con SSI |
| `web/index.html` | `/var/www/caso-e/index.html` | Página del grupo: muestra el nombre pedido, la IP del cliente y si llegó por IPv4 o IPv6 |
| `iniciar.sh` | `/usr/local/bin/iniciar.sh` | Arranca sshd, named y nginx cuando GNS3 levanta el contenedor |
| `Dockerfile` | — | Construye la imagen `caso-e/srv-dmz` con todo lo anterior |

Credenciales: usuario `admin`, contraseña `admin` (SSH solo desde PC-ADMIN, por la política 2).

## Antes de usarla

Completá en `web/index.html` los nombres de los integrantes y confirmá el número de grupo (hoy dice **Grupo 5**, según el bloque sugerido 10.50.0.0/16 que falta confirmar con el profesor).

## Instalación en GNS3

El laboratorio no tiene salida a Internet, así que no se instala nada con `apk` dentro de la maqueta. La imagen se construye afuera y GNS3 la usa ya lista.

### 1. Construir la imagen

**Opción A: en la VM de GNS3** (tiene Docker e Internet). Copiá la carpeta `servicios/` a la VM y construí ahí:

```
scp -r servicios gns3@<IP-de-la-VM-GNS3>:~/servicios      # contraseña: gns3
ssh gns3@<IP-de-la-VM-GNS3>
docker build -t caso-e/srv-dmz ~/servicios
```

**Opción B: en tu PC con Docker Desktop**, y pasarla a la VM:

```
docker build -t caso-e/srv-dmz servicios
docker save caso-e/srv-dmz -o srv-dmz.tar
scp srv-dmz.tar gns3@<IP-de-la-VM-GNS3>:~/
ssh gns3@<IP-de-la-VM-GNS3> docker load -i srv-dmz.tar
```

Si el build termina sin errores, la sintaxis de bind y de nginx ya está validada: el Dockerfile corre `named-checkconf`, `named-checkzone` y `nginx -t`.

### 2. Crear la plantilla

En GNS3: **Edit → Preferences → Docker containers → New**.

| Campo | Valor |
| --- | --- |
| Server | GNS3 VM |
| Image | `caso-e/srv-dmz` (existing image) |
| Name | `SRV-DMZ` |
| Adapters | 1 |
| Start command | vacío (usa el `CMD` de la imagen) |
| Console type | telnet |

### 3. Red del contenedor

Clic derecho sobre SRV-DMZ → **Edit network configuration**, y pegá el bloque de SRV-DMZ que está en `hosts/hosts.md`. Al arrancar, `iniciar.sh` espera a que eth0 tenga 10.50.1.34 y levanta los servicios.

### 4. Comprobar desde la consola del contenedor

```
ps                                        # deben aparecer sshd, named y nginx
dig +short @127.0.0.1 www.g5.eif101o.test A        # 10.50.1.34 (vista interna)
curl -s -H "Host: www.g5.eif101o.test" http://127.0.0.1/ | grep "Grupo"
tail /var/log/named/consultas.log         # cada consulta con el cliente y la vista
```

## Cambios

Un cambio en la zona o en la página se hace en estos archivos, se sube el serial de **las dos** zonas (`AAAAMMDDNN`) y se reconstruye la imagen. Después, en GNS3, se borra y se vuelve a agregar el nodo SRV-DMZ para que tome la imagen nueva. Estos archivos son también el anexo del informe.

## Prueba local hecha

Antes de subirla, la imagen se probó en Docker con un cliente interno (10.50.0.10 / 2001:db8:105:10::10), uno externo (10.60.0.10 / 2001:db8:ffff:100::10) y uno con origen en la WAN (2001:db8:105:ff01::1). Resultados:

| Prueba | Resultado |
| --- | --- |
| `www` A desde adentro | 10.50.1.34 (vista interna) |
| `www` A desde afuera y desde la WAN ff01::/64 | 203.0.113.20 (vista externa) |
| `www` AAAA desde cualquier lado | 2001:db8:105:30::10 |
| `v4` sin AAAA y `v6` sin A | Correcto |
| Consultas por transporte IPv4 e IPv6 | Responden las dos, con la bandera `aa` (autoritativa) |
| Consulta recursiva (`example.com`) | `REFUSED` |
| HTTP por IPv4 e IPv6 con `www`, `v4` y `v6` | La página muestra el nombre pedido, la IP real del cliente y la familia correcta |
| SSH | Puerto 22 abierto |

Lo que esta prueba no cubre es el camino a través del FortiGate y el VIP: eso se verifica en la maqueta con P01–P07.
