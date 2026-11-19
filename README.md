# Clasificador de correos · UMivale · Reto 1 · Sprint 1

Equipo 3 · Víctor Díez Sánchez, Carlos Polo, Alejandro Castro, Alejandro Ruiz Vélez y Joan Balbastre

Aplicación de escritorio (Python + Tkinter) que carga correos de ejemplo y propone,
para cada uno, la **categoría** y el **destino** con su motivo, o lo marca como
**dudoso** explicando por qué. Corresponde a los PBIs **R1** (proponer categoría
y destino) y **R2a** (detectar dudosos) del Sprint 1.

## Cómo ejecutarlo

Necesitáis Python 3.10 o superior. Tkinter viene incluido con Python en Windows y
macOS; en Linux puede que haya que instalarlo (`sudo apt install python3-tk`).

```bash
python main.py              # abre la ventana con los datos de ejemplo
python main.py --consola    # el mismo resultado, en la terminal
python main.py --correos otros.csv --delegaciones otras.csv
```

Pruebas (16 pruebas de los criterios de aceptación):

```bash
python -m pytest            # si tenéis pytest (pip install pytest)
python -m unittest discover -s tests   # sin instalar nada
```

## Qué hace cada archivo

| Archivo | Qué hace |
|---|---|
| `modelo.py` | Clases del dominio: `Correo`, `Remitente`, `Categoria`, `Destino`, `Propuesta`. Sin lógica. |
| `carga.py` | Lee los correos y el listado de delegaciones (CSV o JSON) y da errores claros si falta algo. |
| `clasificador.py` | `ClasificadorPorReglas`: puntúa palabras clave, elige categoría y destino y detecta dudosos. |
| `evaluacion.py` | Resumen para validar: cuántos dudosos y cuántos coinciden con la respuesta correcta. |
| `interfaz.py` | La ventana: tabla de resultados, detalle del correo y barra de estado. Solo muestra. |
| `main.py` | Arranca la ventana o el modo consola. |
| `datos/` | 15 correos de prueba inventados (con su respuesta correcta) y el listado de delegaciones. |
| `tests/` | Pruebas de R1, R2a y de la carga de datos. |

## Cómo decide el clasificador

1. Busca palabras y frases de cada categoría en el asunto (peso 2), en el nombre
   del adjunto (peso 2) y en el cuerpo (peso 1). Las frases largas valen más
   («pago directo de la baja» pesa más que «baja»).
2. Gana la categoría con más puntos. La **confianza** baja si otra categoría le va
   cerca o si hay muy pocas pistas.
3. El **destino** sale de la categoría: la DT del remitente (según el listado) o
   una dirección central (Prestaciones, Médica, Atención al Cliente, Jurídica,
   Organización y Administración, Tecnología).
4. Es **dudoso** si: no hay pistas, hay señales contradictorias, el texto y el
   adjunto apuntan a categorías distintas, hace falta la DT y el remitente no está
   en el listado, la confianza está por debajo del umbral (0,6 por defecto) o
   parece «No relevante» (nunca se archiva sin revisión).

## Decisiones y límites conocidos

- **Los datos de prueba los hemos escrito nosotros** a partir de los ejemplos de
  UMivale. Que coincidan 15 de 15 no demuestra la calidad real: hay que repetir la
  prueba con la muestra de UMivale cuando llegue.
- **Remitente fuera del listado:** solo lo marcamos como dudoso cuando el destino
  es una DT. Si va a una dirección central (un juzgado, un proveedor) no hace falta
  su DT. Es una interpretación nuestra que hay que confirmar con UMivale.
- **Proveedores y facturas:** UMivale menciona dos direcciones posibles; de momento
  usamos «Dir. Organización y Administración».
- No lee el contenido de los adjuntos (solo su nombre), no guarda decisiones, no
  reparte de verdad y no trata respuestas («RE:») ni correos con varias peticiones.
  Eso queda para próximos sprints.
- El umbral (0,6) y los pesos son iniciales: hay que ajustarlos con los datos.
