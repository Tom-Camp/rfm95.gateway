# 📻 RFM95 Receiver 📡

An RFM9x receiver for a Raspberry Pi Zero using an 
[Adafruit RFM95W LoRa Radio Transceiver Breakout](https://www.adafruit.com/product/3072).
The receiver listens for signals on 915MHz radio frequency and upon receipt, relays the message to the data.tom.camp API 
server.

## Hardware Requirements

- Raspberry Pi Zero
- Adafruit RFM95W LoRa Radio Transceiver Breakout


## Wiring

| RFM95W   | Raspberry Pi Zero |
|----------|-------------------|
| GND      | Pin 6 (GND)       |
| VCC      | Pin 1 (3.3V)      |
| SCK      | Pin 23 (SCLK)     |
| MOSI     | Pin 19 (MOSI)     |
| MISO     | Pin 21 (MISO)     |
| NSS      | Pin 24 (CE0)      |
| RST      | Pin 22 (GPIO25)   |  


## Receiving Data

The receiver listens for LoRa packets on the 915MHz frequency. When a packet is received, it decodes the message and 
sends it to the API server. In order to keep the LoRa packet size small, the message includes a shortened device ID. The
receiver uses a mapping of shortened IDs to full device IDs to relay the correct information to the server.

## Contributors

- [Tom Camp](https://github.com/Tom-Camp)

## License
This project is licensed under the Aferro General Public License v3.0 (AGPL-3.0). See the [LICENSE](LICENSE) file for details.