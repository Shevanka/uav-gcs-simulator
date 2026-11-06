# 🚁 UAV Ground Control Station Simulator (UAV-GCS-Simulator)

[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![GUI](https://img.shields.io/badge/GUI-PySide6%20(Qt6)-brightgreen.svg)](https://www.qt.io/qt-for-python)
[![Tests](https://img.shields.io/badge/tests-pytest%20103%20passed-success.svg)](https://docs.pytest.org/)
[![Coverage](https://img.shields.io/badge/coverage-85%25-green.svg)](https://github.com/pytest-dev/pytest-cov)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A high-fidelity, modular desktop Ground Control Station (GCS) and UAV simulation environment built in Python. Designed for studying, testing, and verifying real-time telemetry communication, anomaly detection, fail-safe protocols, and flight path tracking over UDP network sockets.

---

## 📌 Table of Contents

- [Overview](#-overview)
- [System Architecture](#-system-architecture)
- [Key Features](#-key-features)
- [Telemetry Specification](#-telemetry-specification)
- [Installation](#-installation)
- [Quick Start & Usage](#-quick-start--usage)
  - [1. Launch Full Desktop GUI (One-Click Demo)](#1-launch-full-desktop-gui-one-click-demo)
  - [2. Run Standalone UAV Simulator](#2-run-standalone-uav-simulator)
  - [3. Run Headless GCS Receiver](#3-run-headless-gcs-receiver)
- [Testing & Quality Assurance](#-testing--quality-assurance)
- [Interactive Anomaly & Fault Injection Test Bench](#-interactive-anomaly--fault-injection-test-bench)
- [Project Structure](#-project-structure)
- [Roadmap](#-roadmap)
- [License](#-license)

---

## 📖 Overview

In unmanned aerial systems, robust bidirectional communication between the UAV and Ground Control Station is mission-critical. Telemetry parameters (altitude, GPS coordinates, ground speed, heading, battery state, and flight mode) must be received, parsed, validated, and visualized at high frequency without UI stuttering.

The **UAV Ground Control Station Simulator** provides:
1. **UAV Simulator (Producer):** A physics-based kinematics engine modeling flight paths, climb/descent rates, waypoint navigation, and battery discharge.
2. **GCS Receiver & Engine (Consumer):** An asynchronous UDP listener, strict JSON schema and range validator, fail-safe connection monitor, and multi-tier alert engine.
3. **Interactive PySide6 (Qt6) GUI:** A modern, dark-themed flight deck with live metric gauges, a battery health indicator, a real-time 2D GPS trajectory map, altitude/battery strip charts, and an active alert log.

---

## 🏗️ System Architecture

```text
+-------------------------------------------------------+
|                     UAV SIMULATOR                     |
|  - Kinematics Engine (Climb / Descent / Waypoints)    |
|  - Battery Discharge Model                            |
|  - Telemetry Generator (ISO 8601 UTC JSON)            |
|  - Anomaly Injector (Low Battery, Ceiling, Blackout)  |
+---------------------------+---------------------------+
                            |
                            | UDP Datagrams (JSON)
                            v
+-------------------------------------------------------+
|                    GCS CORE ENGINE                    |
|  - Asynchronous UDP Receiver (Non-blocking Thread)    |
|  - UTF-8 Decoder & JSON Parser                        |
|  - Schema & Range Validator (Section 9.2 Compliance)  |
|  - Heartbeat & Connection Timeout Monitor (5s rule)   |
|  - Multi-Category Alert Manager (Battery, Alt, Comm)  |
|  - Structured Telemetry Logger (JSONL / CSV)          |
+---------------------------+---------------------------+
                            |
                            | Qt Signals (Thread-Safe Bridge)
                            v
+-------------------------------------------------------+
|                  PYSIDE6 DESKTOP GUI                  |
|  - Aircraft Flight State Cards (Mode, Armed, Coordinates)|
|  - Battery Progress Bar with Dynamic Severity Badges  |
|  - Real-Time 2D Flight Path & Heading Marker          |
|  - Altitude & Battery Strip Charts (Matplotlib)       |
|  - Anomaly Injection & Test Bench Control Panel       |
|  - Interactive System & Flight Alert Log Table        |
+-------------------------------------------------------+
```

---

## ✨ Key Features

| Category | Feature | Status |
|---|---|---|
| **Simulation** | Real-time UAV flight dynamics & waypoint tracking | **P0 (Implemented)** |
| **Networking** | Non-blocking UDP socket sender & receiver | **P0 (Implemented)** |
| **Validation** | Strict JSON schema & physical boundary validation | **P0 (Implemented)** |
| **Fail-Safe** | Connection state tracking (DISCONNECTED -> CONNECTED -> TIMEOUT) | **P0 (Implemented)** |
| **Monitoring** | Real-time metric cards (Altitude, Speed, Heading, Lat/Lon) | **P0 (Implemented)** |
| **Power System**| Battery threshold monitor (NORMAL, WARNING, CRITICAL, EMERGENCY) | **P0 (Implemented)** |
| **Alerts** | Abnormal condition detection with severity levels & deduplication | **P0 (Implemented)** |
| **Logging** | Thread-safe session logging in `.jsonl` or `.csv` | **P1 (Implemented)** |
| **Visualization**| Embedded 2D GPS flight track & altitude/battery strip charts | **P1 (Implemented)** |
| **Testing** | Interactive Anomaly & Fault Injection Test Bench | **Bonus (Implemented)** |

---

## 📡 Telemetry Specification

### JSON Payload Schema (RFC 8259)

```json
{
  "timestamp": "2026-11-06T10:00:00Z",
  "system_id": 1,
  "component_id": 1,
  "latitude": -7.2756,
  "longitude": 112.7949,
  "altitude": 120.5,
  "ground_speed": 15.2,
  "heading": 90.0,
  "battery": 85.0,
  "flight_mode": "AUTO",
  "armed": true
}
```

### Validation Constraints

| Field | Type | Rule / Boundary | Action on Violation |
|---|---|---|---|
| `timestamp` | String | Valid ISO 8601 format | Reject packet, log error |
| `system_id` | Integer | $1 \le \text{id} \le 255$ | Reject packet, log error |
| `component_id` | Integer | $1 \le \text{id} \le 255$ | Reject packet, log error |
| `latitude` | Float | $-90.0^\circ \le \text{lat} \le 90.0^\circ$ | Reject packet, log error |
| `longitude` | Float | $-180.0^\circ \le \text{lon} \le 180.0^\circ$ | Reject packet, log error |
| `altitude` | Float | $0.0\,\text{m} \le \text{alt} \le 10,000.0\,\text{m}$ | Reject packet, log error |
| `ground_speed` | Float | $\text{speed} \ge 0.0\,\text{m/s}$ | Reject packet, log error |
| `heading` | Float | $0.0^\circ \le \text{heading} \le 360.0^\circ$ | Reject packet, log error |
| `battery` | Number | $0.0\% \le \text{battery} \le 100.0\%$ | Reject packet, log error |
| `flight_mode` | String | `MANUAL`, `STABILIZE`, `ALT_HOLD`, `AUTO`, `LOITER`, `GUIDED`, `RTL`, `LAND` | Reject packet, log error |
| `armed` | Boolean | Strict `True` / `False` | Reject packet, log error |

> **State Protection Rule:** When an incoming packet fails validation or is malformed, the GCS discards it, increments the rejected counter, logs the error, and preserves the last known valid telemetry state.

---

## 💻 Installation

### Prerequisites
- Python 3.11 or newer (tested on Python 3.12, 3.13, 3.14).
- Windows 11 or Linux (Ubuntu 22.04+).

### Setup

```bash
# Clone the repository
git clone https://github.com/your-username/uav-gcs-simulator.git
cd uav-gcs-simulator

# Create and activate virtual environment (recommended)
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## 🚀 Quick Start & Usage

### 1. Launch Full Desktop GUI (One-Click Demo)

To launch the desktop interface with both the receiver and simulator automatically running:

```bash
python main.py --mode all
```

Or run the GUI normally and use the top toolbar buttons to start/stop the receiver and simulator:

```bash
python main.py
```

### 2. Run Standalone UAV Simulator

Run only the UAV flight simulation engine in the console:

```bash
python main.py --mode sim --host 127.0.0.1 --port 50051 --interval 1.0
```

### 3. Run Headless GCS Receiver

Run the GCS core engine headlessly in a server or terminal environment:

```bash
python main.py --mode headless-gcs --host 127.0.0.1 --port 50051 --timeout 5.0
```

---

## 🧪 Testing & Quality Assurance

The codebase includes an extensive test suite built with `pytest` covering all core modules, networking loopback, kinematics, schema validation, state machines, and offscreen UI updates.

To execute tests and view the coverage report:

```bash
pytest -v --cov=communication --cov=gcs --cov=simulator --cov=ui --cov-report=term-missing
```

### Test Summary
- **103 unit tests** passing with **85% overall coverage** (and >85% on core modules).
- Comprehensive test coverage across all boundary conditions, invalid data types, blackout timeouts, and malformed JSON packets.

---

## 🛠️ Interactive Anomaly & Fault Injection Test Bench

The GUI provides an integrated **Anomaly Injection Panel** specifically designed for live demonstrations and testing:

1. **⚡ Inject Low Battery (15%):** Instantly drops UAV battery below the 20% critical threshold to trigger GCS visual alerts and change battery status badges to `EMERGENCY`.
2. **⛰️ Inject Altitude Ceiling (650m):** Forces altitude above operational limits to trigger an altitude ceiling warning.
3. **⏱️ 6s Blackout (Test Timeout):** Suspends UDP packets for 6 seconds. When no packet is received for 5.0s, the GCS connection status transitions from `CONNECTED` to `TIMEOUT` and fires a critical communication alert. Upon resumption, it returns to `CONNECTED`.
4. **⚠️ Send Malformed JSON:** Transmits broken byte payloads (`{"timestamp": ... unclosed`) to demonstrate that the GCS parser rejects corrupt packets without crashing.
5. **🚫 Send Out-of-bounds Data:** Transmits invalid field values (e.g. altitude 15,000m) to prove schema validator rejection.
6. **🏠 Command RTL Mode:** Commands Return-To-Launch flight mode.

---

## 📂 Project Structure

```text
uav-gcs-simulator/
│
├── config/
│   └── settings.json             # Network, thresholds, and logging configuration
│
├── simulator/
│   ├── __init__.py
│   ├── flight_state.py           # Physical kinematics, waypoint navigation, battery model
│   ├── telemetry_generator.py    # Standard payload and anomaly generators
│   └── uav.py                    # UAV simulator loop and UDP transmission worker
│
├── communication/
│   ├── __init__.py
│   ├── protocol.py               # Enums, dataclasses, schemas, and timestamps
│   ├── sender.py                 # UDP socket sender
│   └── receiver.py               # Asynchronous UDP socket receiver thread
│
├── gcs/
│   ├── __init__.py
│   ├── telemetry.py              # Telemetry processor, UTF-8 decoder, state cache
│   ├── validator.py              # Field type and range validation (Section 9.2)
│   ├── monitor.py                # Heartbeat tracking and 5s timeout state machine
│   ├── alerts.py                 # Multi-tier alert manager with deduplication
│   └── logger.py                 # Thread-safe JSONL and CSV logging
│
├── ui/
│   ├── __init__.py
│   ├── dashboard.py              # PySide6 main window & thread-safe signal bridge
│   ├── telemetry_panel.py        # Live parameter gauges and battery status card
│   ├── alert_panel.py            # Link health statistics and alert table
│   └── map_panel.py              # Matplotlib 2D GPS flight track & strip charts
│
├── tests/
│   ├── test_validator.py         # Schema and boundary validation unit tests
│   ├── test_telemetry.py         # Parser, corrupt JSON, and battery status tests
│   ├── test_alerts.py            # Battery, altitude, timeout, and listener tests
│   ├── test_communication.py     # Real UDP loopback and connection monitor tests
│   ├── test_flight_state.py      # Kinematics and navigation tests
│   ├── test_simulator.py         # UAV simulator lifecycle and anomaly tests
│   ├── test_logger.py            # JSONL and CSV file logging tests
│   └── test_ui.py                # Offscreen Qt UI rendering tests
│
├── main.py                       # Unified CLI and application entrypoint
├── requirements.txt              # Production and development dependencies
├── .gitignore                    # Python, coverage, log, and editor ignores
├── README.md                     # Documentation and architecture guide
├── SECURITY.md                   # Security reporting policy
└── LICENSE                       # MIT Open Source License
```

---

## 🔮 Roadmap

- [ ] **MAVLink Protocol Integration:** Support `pymavlink` parsing for standard `HEARTBEAT`, `GLOBAL_POSITION_INT`, and `SYS_STATUS` packets.
- [ ] **ArduPilot SITL Integration:** Direct TCP/UDP bridge to ArduPilot Software-In-The-Loop simulation.
- [ ] **Interactive OpenStreetMap (Folium/Leaflet):** Interactive zoomable map widget.
- [ ] **Simulated Camera Stream:** Synthetic optical camera feed with OpenCV computer vision filters.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
