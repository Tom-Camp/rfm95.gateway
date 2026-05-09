# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LoRa radio receiver running on a Raspberry Pi Zero with an Adafruit RFM95W breakout. Listens on 915MHz, decodes msgpack packets, and relays sensor readings to the `data.tom.camp` API.

`main.py` is currently a stub. The reference implementation is `receiver.old.py`, which is being rewritten into `main.py`.

## Commands

This project uses `uv` for package management.

```bash
uv run main.py        # Run the receiver
uv add <package>      # Add a dependency
uv sync               # Install dependencies from lockfile
```

Pre-commit hooks (ruff, mypy, bandit, commitizen) run on commit. To run manually:

```bash
uv run ruff check --fix .
uv run ruff format .
uv run mypy .
pre-commit run --all-files
```

Commit messages must follow [Conventional Commits](https://www.conventionalcommits.org/) (enforced by commitizen).

## Architecture

The core is a `LoraReceiver` class that:

1. **Initializes hardware** — SPI bus via `busio`, chip-select on `board.CE1`, reset on `board.D25`, wrapped by `adafruit_rfm9x.RFM9x` at 915MHz.
2. **Polls for packets** — calls `radio.receive(with_ack=False)` in a tight loop (100ms sleep). Returns `None` on timeout.
3. **Decodes packets** — `struct.unpack_from('>BhH', raw)` → `(device_num, temp_raw, moisture_raw)`. Temperature is stored as `int(celsius * 10)`, so divide by 10 to recover. Packet is 5 bytes total.
4. **Resolves credentials** — `device_num` (uint8) maps to `DEVICE_{N}_DEVICE_ID` and `DEVICE_{N}_API_KEY` in `.env`. `pydantic-settings` loads all env vars; `get_credentials(n)` looks up `device_{n}_device_id` / `device_{n}_api_key` in `model_extra`.
5. **POSTs to API** — sends `{"temperature": float, "moisture": int}` JSON to `API_URL` with `X-API-Key` and `X-Device-Id` headers. Uses `httpx` with a 10s timeout and `tenacity` retry (3 attempts, exponential backoff 2–30s).

Logging uses `loguru` with rotating files under `logs/` (INFO and ERROR levels) plus stderr.

### Sender packet format (garden.sensors)

```python
struct.pack('>BhH', DEVICE_NUM, int(temp * 10), moisture)
# byte 0:   uint8  — device number (DEVICE_NUM constant in garden.sensors/main.py)
# bytes 1-2: int16  — temperature × 10 (e.g. 21.5°C → 215)
# bytes 3-4: uint16 — raw moisture capacitance (0–4095)
```

## Environment Variables

```
API_URL=https://data.tom.camp/api/v1/data/
DEVICE_1_DEVICE_ID=<uuid>
DEVICE_1_API_KEY=<key>
# Add DEVICE_2_*, DEVICE_3_*, etc. for additional sensors
```

## Hardware

Targets Raspberry Pi Zero. SPI wiring (RFM95W → RPi):

| RFM95W | RPi Pin        |
|--------|----------------|
| GND    | Pin 6 (GND)    |
| VCC    | Pin 1 (3.3V)   |
| SCK    | Pin 23 (SCLK)  |
| MOSI   | Pin 19 (MOSI)  |
| MISO   | Pin 21 (MISO)  |
| NSS    | Pin 24 (CE0)   |
| RST    | Pin 22 (GPIO25)|

Radio config: 125kHz bandwidth, SF7, coding rate 5, CRC enabled, TX power 23dBm.
