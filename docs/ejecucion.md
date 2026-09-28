# Resultado de la ejecucion del prototipo

Comando ejecutado:

```bash
python src/prototype.py
```

Salida completa del programa:

```text
=== Simulacion de smartwatch ===
Pasos simulados: 60

--- Escenario: online (Wi-Fi) ---
  estado: modo=online pendientes=0
  almacenamiento local: {'records': 15, 'avg_hr': 78.9}

--- Escenario: degradado (solo BLE) ---
  estado: modo=degraded pendientes=0
  almacenamiento local: {'records': 30, 'avg_hr': 80.2}

--- Escenario: offline (sin red) ---
  estado: modo=offline pendientes=15
  almacenamiento local: {'records': 45, 'avg_hr': 79.2}

--- Escenario: online (LTE) ---
  estado: modo=online pendientes=0
  almacenamiento local: {'records': 60, 'avg_hr': 79.2}

=== Resultado final ===
UI ultima lectura: {'hr': 89, 'activity': 'walking'}
Almacenamiento local: {'records': 60, 'avg_hr': 79.2}
Nube: {'records_received': 60, 'critical_events_received': 0, 'avg_hr': 79.2}
```

## Interpretacion de los resultados

| Escenario | Modo | Datos pendientes | Comportamiento observado |
|-----------|------|------------------|--------------------------|
| online (Wi-Fi) | online | 0 | Los lotes se envian a la nube de forma inmediata |
| degradado (solo BLE) | degraded | 0 | La sincronizacion se realiza a traves del telefono por Bluetooth |
| offline (sin red) | offline | 15 | Sin conexion: los datos se acumulan en la cola de sincronizacion local |
| online (LTE) | online | 0 | Al recuperar conexion, la cola pendiente se sincroniza y queda vacia |

Observaciones:

- El almacenamiento local conserva los 60 registros (dentro del limite de retencion) y calcula la frecuencia cardiaca promedio (79.2).
- En el escenario offline se acumulan 15 registros pendientes; al pasar al escenario LTE esos 15 se sincronizan (pendientes=0).
- La nube recibe 60 registros en total, confirmando que todo lo almacenado localmente finalizo sincronizado.
- No se generaron eventos criticos en esta ejecucion (la probabilidad de caida es baja por paso); si ocurrieran, se imprimirian como alertas en la UI y se sincronizarian con prioridad.
