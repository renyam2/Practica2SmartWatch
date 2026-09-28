# Practica 2: Arquitectura de una aplicacion para dispositivo inteligente

## Escenario seleccionado

Reloj inteligente (Smartwatch)

## Contenido del proyecto

| Archivo | Descripcion |
|---------|-------------|
| `docs/arquitectura.md` | Propuesta arquitectonica completa del sistema |
| `docs/diagramas.md` | Diagramas del modelo arquitectonico (Mermaid) |
| `docs/ejecucion.md` | Salida de la ejecucion del prototipo e interpretacion |
| `docs/entrega_final.md` | Documento final de entrega con todos los requisitos documentados |
| `src/prototype.py` | Prototipo en Python que simula los componentes y su comunicacion |
| `src/requirements.txt` | Dependencias del prototipo |

## Resumen

Se propone una arquitectura en capas para un reloj inteligente que:

- Procesa localmente los datos de sensores (frecuencia cardiaca, acelerometria, GPS) para ahorrar energia.
- Almacena informacion localmente con politicas de retencion limitadas.
- Sincroniza con una aplicacion movil (companion app) y con servidores en la nube cuando hay conectividad.
- Opera de forma autònoma (modo offline) cuando no hay conexion a Internet.
- Aplica mecanismos de seguridad: cifrado en reposo, en transitoy autenticacion.

## Como ejecutar el prototipo

```bash
python src/prototype.py
```

El prototipo simula un ciclo de trabajo del reloj: lectura de sensores, procesamiento local, almacenamiento, deteccion de conectividad, sincronizacion con la nube y comportamiento offline.
