# Cliente del laboratorio: Alpine con las herramientas de prueba de la matriz (dig, curl, ssh, ping, ip).
# Se construye una vez en la VM de GNS3 (que sí tiene Internet), igual que caso-e/srv-dmz:
#   docker build -t caso-e/cliente servicios/cliente
# La plantilla Alpine del servidor arranca con udhcpc y se queda esperando un DHCP que no existe en la maqueta.
# Esta imagen arranca directo en un shell para que se aplique la red estática de hosts/hosts.md.
FROM alpine:3.20
RUN apk add --no-cache bind-tools curl openssh-client iproute2 iputils tcpdump
CMD ["/bin/sh"]
