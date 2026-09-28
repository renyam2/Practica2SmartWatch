"""
Prototipo de la arquitectura de un reloj inteligente (smartwatch).

Simula los principales componentes del sistema y su comunicacion:
  - Sensores (PPG, acelerometro, GPS)
  - Motor de procesamiento local
  - Almacenamiento local con cola de sincronizacion y retencion limitada
  - Gestor de conectividad (online / degradado / offline)
  - Telefono (companion app) y nube
  - Modulo de seguridad (cifrado y autenticacion)

Uso:
    python src/prototype.py
"""

import json
import hashlib
import random
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Modelo de datos
# ---------------------------------------------------------------------------

@dataclass
class SensorReading:
    """Lectura normalizada de los sensores en un instante."""
    timestamp: float
    heart_rate: int          # latidos por minuto
    activity: str            # "idle", "walking", "running", "sleep"
    location: Optional[tuple]  # (lat, lon) o None si GPS apagado
    fell: bool = False       # evento de caida detectado


@dataclass
class HealthEvent:
    """Evento critico que debe conservarse y sincronizarse con prioridad."""
    timestamp: float
    kind: str                # "fall", "high_hr", "low_hr"
    critical: bool = True


# ---------------------------------------------------------------------------
# Sensores
# ---------------------------------------------------------------------------

class Sensors:
    """Capa de drivers de sensores. Genera lecturas normalizadas."""

    def __init__(self, rng: random.Random):
        self.rng = rng
        self.gps_enabled = True

    def read(self) -> SensorReading:
        activity = self.rng.choices(
            ["idle", "walking", "running", "sleep"],
            weights=[50, 30, 15, 5],
        )[0]
        base_hr = {"idle": 60, "walking": 90, "running": 140, "sleep": 48}[activity]
        heart_rate = max(35, base_hr + self.rng.randint(-8, 8))
        location = (
            (40.0 + self.rng.random() * 0.01, -3.0 + self.rng.random() * 0.01)
            if self.gps_enabled
            else None
        )
        fell = activity == "running" and self.rng.random() < 0.02
        return SensorReading(
            timestamp=time.time(),
            heart_rate=heart_rate,
            activity=activity,
            location=location,
            fell=fell,
        )


# ---------------------------------------------------------------------------
# Motor de procesamiento local
# ---------------------------------------------------------------------------

class LocalProcessor:
    """
    Procesa en el dispositivo toda la informacion critica y de baja
    latencia: frecuencia cardiaca, clasificacion de actividad y deteccion
    de caida. No depende de la red.
    """

    def process(self, reading: SensorReading) -> dict:
        result = {
            "heart_rate": reading.heart_rate,
            "activity": reading.activity,
            "alerts": [],
        }
        # Reglas de salud evaluadas localmente (baja latencia).
        if reading.heart_rate > 160:
            result["alerts"].append(HealthEvent(reading.timestamp, "high_hr"))
        if reading.heart_rate < 40:
            result["alerts"].append(HealthEvent(reading.timestamp, "low_hr"))
        if reading.fell:
            result["alerts"].append(HealthEvent(reading.timestamp, "fall"))
        return result


# ---------------------------------------------------------------------------
# Almacenamiento local con cola de sincronizacion
# ---------------------------------------------------------------------------

class LocalStorage:
    """
    Base de datos embebida del reloj.

    - Conserva los ultimos N lecturas (retencion limitada por memoria).
    - Mantiene una cola de sincronizacion para datos pendientes de enviar.
    - Prioriza siempre los eventos criticos de salud.
    """

    def __init__(self, max_records: int = 500, max_queue: int = 200):
        self.records = deque(maxlen=max_records)
        self.queue = deque(maxlen=max_queue)
        self.events = deque(maxlen=50)

    def store(self, reading: SensorReading, result: dict) -> None:
        self.records.append(
            {
                "t": reading.timestamp,
                "hr": reading.heart_rate,
                "activity": reading.activity,
                "loc": reading.location,
            }
        )
        for event in result["alerts"]:
            self.events.append(event)
        # Todo lo nuevo entra a la cola de sincronizacion si no esta sincronizado.
        self.queue.append(
            {
                "t": reading.timestamp,
                "hr": reading.heart_rate,
                "activity": reading.activity,
            }
        )

    def pending(self) -> int:
        return len(self.queue)

    def drain(self, batch_size: int = 20) -> list:
        """Extrae un lote de datos pendientes (sincronizacion por lotes)."""
        batch = []
        while self.queue and len(batch) < batch_size:
            batch.append(self.queue.popleft())
        return batch

    def drain_events(self) -> list:
        """Extrae los eventos criticos pendientes (prioridad alta)."""
        events = list(self.events)
        self.events.clear()
        return events

    def summary(self) -> dict:
        if not self.records:
            return {"records": 0, "avg_hr": None}
        avg_hr = sum(r["hr"] for r in self.records) / len(self.records)
        return {"records": len(self.records), "avg_hr": round(avg_hr, 1)}


# ---------------------------------------------------------------------------
# Gestor de conectividad
# ---------------------------------------------------------------------------

class ConnectivityManager:
    """
    Decide el modo de operacion del reloj:
      - online:    Wi-Fi o LTE disponible (sincronizacion directa).
      - degraded:  solo Bluetooth con el telefono (sincronizacion via BLE).
      - offline:   sin red (acumula en la cola local).
    """

    def __init__(self, rng: random.Random):
        self.rng = rng
        self.wifi = False
        self.lte = False
        self.bluetooth = True

    def set(self, wifi: bool, lte: bool, bluetooth: bool) -> None:
        self.wifi, self.lte, self.bluetooth = wifi, lte, bluetooth

    def mode(self) -> str:
        if self.wifi or self.lte:
            return "online"
        if self.bluetooth:
            return "degraded"
        return "offline"


# ---------------------------------------------------------------------------
# Telefono (companion app) y nube
# ---------------------------------------------------------------------------

class Phone:
    """Puente entre el reloj y la nube mediante Bluetooth (BLE)."""

    def __init__(self, cloud: "Cloud"):
        self.cloud = cloud
        self.link_up = True

    def sync(self, batch: list, events: list) -> int:
        if not self.link_up:
            return 0
        return self.cloud.ingest(batch, events)


class Cloud:
    """
    Backend en la nube: API gateway, servicio de salud y base de datos.
    Recibe lotes de datos, los agrega y genera un resumen.
    """

    def __init__(self):
        self.total_records = 0
        self.total_events = 0
        self.hr_sum = 0

    def ingest(self, batch: list, events: list) -> int:
        self.total_records += len(batch)
        self.total_events += len(events)
        self.hr_sum += sum(r["hr"] for r in batch)
        return len(batch) + len(events)

    def report(self) -> dict:
        avg_hr = round(self.hr_sum / self.total_records, 1) if self.total_records else None
        return {
            "records_received": self.total_records,
            "critical_events_received": self.total_events,
            "avg_hr": avg_hr,
        }


# ---------------------------------------------------------------------------
# Modulo de seguridad
# ---------------------------------------------------------------------------

class SecurityModule:
    """
    - Cifra los lotes antes de transmitirlos (simulacion de cifrado en transito).
    - Deriva una clave local a partir de una semilla (simulacion de Secure Element).
    - Verifica la integridad de los paquetes con un resumen (hash).
    """

    def __init__(self, seed: str = "secure-element-seed"):
        self.key = hashlib.sha256(seed.encode()).digest()

    def encrypt_payload(self, payload: dict) -> dict:
        raw = json.dumps(payload, sort_keys=True).encode()
        # Simulacion de cifrado: XOR con la clave derivada.
        cipher = bytes(b ^ self.key[i % len(self.key)] for i, b in enumerate(raw))
        return {
            "cipher": cipher.hex(),
            "integrity": hashlib.sha256(cipher).hexdigest()[:16],
        }

    def verify_integrity(self, payload: dict, expected_hash: str) -> bool:
        return payload["integrity"] == expected_hash


# ---------------------------------------------------------------------------
# Smartwatch (orquestador de los componentes)
# ---------------------------------------------------------------------------

class Smartwatch:
    """
    Integra todos los componentes del dispositivo y define el flujo:
      sensores -> motor local -> almacenamiento -> conectividad -> sincronizacion
    """

    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)
        self.sensors = Sensors(self.rng)
        self.processor = LocalProcessor()
        self.storage = LocalStorage()
        self.connectivity = ConnectivityManager(self.rng)
        self.phone = Phone(Cloud())
        self.security = SecurityModule()
        self.ui = WatchUI()

    def step(self) -> dict:
        # 1. Lectura de sensores.
        reading = self.sensors.read()
        # 2. Procesamiento local (critico, sin red).
        result = self.processor.process(reading)
        # 3. Almacenamiento local con retencion limitada.
        self.storage.store(reading, result)
        # 4. Actualizar interfaz de usuario.
        self.ui.show(reading, result)
        # 5. Sincronizacion segun el modo de conectividad.
        return self._sync()

    def _sync(self) -> dict:
        mode = self.connectivity.mode()
        if mode == "offline":
            return {
                "mode": mode,
                "synced": 0,
                "pending": self.storage.pending(),
                "note": "sin conexion: datos acumulados en cola local",
            }
        batch = self.storage.drain(batch_size=20)
        events = self.storage.drain_events()
        payload = {"batch": batch, "events": [e.__dict__ for e in events]}
        # Cifrado e integridad antes de transmitir.
        encrypted = self.security.encrypt_payload(payload)
        synced = self.phone.sync(batch, events)
        return {
            "mode": mode,
            "synced": synced,
            "pending": self.storage.pending(),
            "integrity_ok": self.security.verify_integrity(
                encrypted, encrypted["integrity"]
            ),
        }


class WatchUI:
    """
    Capa de interaccion con el usuario: pantalla, vibracion y voz.
    Simula la retroalimentacion inmediata al usuario.
    """

    def __init__(self):
        self.last_display = None

    def show(self, reading: SensorReading, result: dict) -> None:
        self.last_display = {
            "hr": reading.heart_rate,
            "activity": reading.activity,
        }
        # Alertas: vibracion + voz (haptica y audio).
        for event in result["alerts"]:
            print(f"  [UI] ALERTA {event.kind}: vibracion + aviso de voz")


# ---------------------------------------------------------------------------
# Simulacion completa
# ---------------------------------------------------------------------------

def run_simulation(steps: int = 60) -> None:
    watch = Smartwatch()
    cloud = watch.phone.cloud

    print("=== Simulacion de smartwatch ===")
    print(f"Pasos simulados: {steps}")
    print()

    # Escenarios de conectividad a lo largo de la simulacion.
    scenarios = [
        ("online (Wi-Fi)", dict(wifi=True, lte=False, bluetooth=True)),
        ("degradado (solo BLE)", dict(wifi=False, lte=False, bluetooth=True)),
        ("offline (sin red)", dict(wifi=False, lte=False, bluetooth=False)),
        ("online (LTE)", dict(wifi=False, lte=True, bluetooth=False)),
    ]
    for name, cfg in scenarios:
        watch.connectivity.set(**cfg)
        print(f"--- Escenario: {name} ---")
        for _ in range(steps // len(scenarios)):
            watch.step()
        status = watch._sync()
        print(f"  estado: modo={status['mode']} pendientes={status['pending']}")
        print(f"  almacenamiento local: {watch.storage.summary()}")
        print()

    print("=== Resultado final ===")
    print(f"UI ultima lectura: {watch.ui.last_display}")
    print(f"Almacenamiento local: {watch.storage.summary()}")
    print(f"Nube: {cloud.report()}")


if __name__ == "__main__":
    run_simulation()
