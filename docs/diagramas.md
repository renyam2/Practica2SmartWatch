# Diagramas del modelo arquitectonico

## 1. Diagrama general de componentes

```mermaid
graph TB
    subgraph Smartwatch
        S[Sensores: PPG, acelerometro, giroscopio, GPS, microfonos]
        M[Motor de procesamiento local]
        DB[(Almacenamiento local: SQLite + cola de sincronizacion)]
        C[Gestor de conectividad]
        E[Gestor de energia]
        SEC[Modulo de seguridad local: cifrado, Secure Element]
        UI[UI tactil, voz, vibracion]
    end

    subgraph Telefono
        APP[Companion App]
    end

    subgraph Nube
        GW[API Gateway]
        HS[Servicio de salud y ML]
        NDB[(Base de datos en la nube)]
        NOT[Servicio de notificaciones]
        PAY[Servicio de pagos]
        DASH[Dashboard web]
    end

    S --> M
    M --> DB
    M --> UI
    E --> M
    SEC --> DB
    C --> APP
    APP --> GW
    C -->|LTE opcional| GW
    GW --> HS
    GW --> NOT
    GW --> PAY
    HS --> NDB
    NOT --> APP
    NOT -->|push| C
    DASH --> NDB
```

## 2. Flujo de datos de una sesion de actividad

```mermaid
sequenceDiagram
    participant S as Sensores
    participant M as Motor local
    participant DB as Almacenamiento local
    participant C as Gestor de conectividad
    participant T as Telefono (BLE)
    participant N as Nube

    S->>M: datos crudos (PPG, acelerometro, GPS)
    M->>M: calculo de FC, clasificacion de actividad
    M->>DB: escritura en lotes (batch)
    M->>M: UI actualiza pantalla
    C->>C: verifica conectividad
    alt hay conexion (BLE o LTE)
        C->>T: envia lote de datos por BLE
        T->>N: HTTPS/TLS (lotes)
        N->>N: agrega y analiza (ML pesado)
        N-->>T: respuesta / notificaciones
    else sin conexion (offline)
        C->>DB: acumula en cola de sincronizacion
        Note over DB: retencion limitada, prioriza eventos criticos
    end
```

## 3. Decision de procesamiento local vs nube

```mermaid
flowchart TD
    D[Datos del sensor] --> Q1{Es critico o de baja latencia?}
    Q1 -->|si| L[Procesar localmente]
    Q1 -->|no| Q2{Es de largo plazo o pesado?}
    Q2 -->|si| CLOUD[Procesar en la nube]
    Q2 -->|no| L
    L --> ST[Almacenar localmente con retencion limitada]
    ST --> SYNC{Hay conexion?}
    SYNC -->|si| UP[Enviar a la nube en lotes]
    SYNC -->|no| WAIT[Quedar en cola hasta recuperar conexion]
```

## 4. Diagrama de estados del modo de conectividad

```mermaid
stateDiagram-v2
    [*] --> Online
    Online --> Degradado: sin Wi-Fi/LTE, con BLE
    Online --> Offline: sin Wi-Fi/LTE ni BLE
    Degradado --> Online: recupera Wi-Fi/LTE
    Degradado --> Offline: pierde BLE
    Offline --> Degradado: recupera BLE
    Offline --> Online: recupera Wi-Fi/LTE
    Offline --> Offline: acumula cola, retencion limitada
    Degradado --> Degradado: sincroniza por BLE en lotes
    Online --> Online: sincroniza directo o por BLE
```
