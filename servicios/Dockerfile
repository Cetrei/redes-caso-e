# SRV-DMZ — imagen para GNS3 con bind9, nginx y OpenSSH ya instalados y configurados.
# Se construye una vez en la VM de GNS3 (que sí tiene Internet):
#   docker build -t caso-e/srv-dmz servicios/
# Dentro del laboratorio no hay salida a Internet, por eso no se instala nada con apk en la maqueta.
FROM alpine:3.20

RUN apk add --no-cache bind bind-tools nginx openssh iproute2 curl \
 && adduser -D -s /bin/sh admin \
 && echo "admin:admin" | chpasswd \
 && ssh-keygen -A \
 && mkdir -p /etc/bind/zonas /var/log/named /var/run/named /var/www/caso-e /run/nginx \
 && chown -R named:named /var/log/named /var/run/named

COPY dns/named.conf /etc/bind/named.conf
COPY dns/db.g5.eif101o.test.interna dns/db.g5.eif101o.test.externa /etc/bind/zonas/
COPY web/caso-e.conf /etc/nginx/http.d/default.conf
COPY web/index.html /var/www/caso-e/index.html
COPY iniciar.sh /usr/local/bin/iniciar.sh

# Si algún archivo tiene un error de sintaxis, la imagen no se construye.
RUN chmod +x /usr/local/bin/iniciar.sh \
 && named-checkconf /etc/bind/named.conf \
 && named-checkzone g5.eif101o.test /etc/bind/zonas/db.g5.eif101o.test.interna \
 && named-checkzone g5.eif101o.test /etc/bind/zonas/db.g5.eif101o.test.externa \
 && nginx -t

EXPOSE 22 53/udp 53/tcp 80
CMD ["/usr/local/bin/iniciar.sh"]
