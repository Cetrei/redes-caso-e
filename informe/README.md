# Informe Parte I

Entrega: `Grupo_05_Proyecto_Parte_I.pdf` en AVI (sección "Sem15-Te7") a más tardar el **31 de octubre**. Entre 8 y 15 páginas de contenido, sin contar portada, índice ni anexos. Citas en APA. Las imágenes propias llevan "Elaboración propia".

## Archivos

| Archivo | Qué es |
| --- | --- |
| `Grupo_05_Proyecto_Parte_I.docx` | El informe completo: portada, índice, las nueve secciones del enunciado, referencias y anexos |
| `fuente/construir_informe.py` | Genera el `.docx`: `uv run fuente/construir_informe.py <raíz del repo> <salida.docx>` |
| `fuente/figuras/topologia-informe.svg` | Diagrama lógico en vertical, para imprimir |
| `fuente/figuras/topologia.png` | Mismo diagrama en PNG, el que se inserta en el Word |

## Antes de entregar

En Word, use Ctrl + F con el prefijo indicado. Cada marca amarilla lleva un identificador.

1. `CAP-01` a `CAP-04`: cada recuadro amarillo indica el dispositivo, el comando o acción y lo que debe verse. Reemplace el recuadro por la captura y deje el pie de figura.
2. `CAP-03` y `CAP-04` se toman en la consola gráfica (VNC) de PC-ADMIN, que trae Firefox: doble clic en el nodo. La terminal de PC-USER para el segundo comando de `CAP-04` está en clic derecho, Auxiliary console. Primero acepta la advertencia del certificado de https://10.50.1.49.
3. Antes de tomar `CAP-01` y `CAP-02`, reconstruya la imagen de SRV-DMZ (`uv run gns3ctl.py imagen` en `automatizacion/`) para que la página muestre los nombres de los integrantes.
4. En Word, actualice el índice (clic derecho sobre la tabla de contenido, Actualizar campo) para que los números de página queden bien.
5. Verifique que el cuerpo no pase de 15 páginas al insertar las capturas, y guarde como PDF con el nombre `Grupo_05_Proyecto_Parte_I.pdf`.
