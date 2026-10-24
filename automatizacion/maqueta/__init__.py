"""Motor que arma y opera la maqueta del Caso E en GNS3 a partir de los archivos de topologia/.

Capas, de adentro hacia afuera (cada una solo conoce a las de adentro):

  errores, modelo      dominio: la topologia como datos inmutables
  repositorio          lectura y escritura de topologia/ y de las configs que referencia
  gns3, consola, ssh   adaptadores hacia el exterior (API REST, telnet, SSH); cada uno
                       recibe su transporte, asi las pruebas usan uno falso
  tipos, validacion    reglas de cada tipo de nodo y de la topologia
  servicios            casos de uso: construir, ciclo de vida, posiciones, fortigate, licencia, imagenes
  aplicacion           raiz de composicion: unico lugar que crea servicios y dependencias reales
  comandos, cli        la linea de comandos

Guia para el grupo: automatizacion/README.md
"""
