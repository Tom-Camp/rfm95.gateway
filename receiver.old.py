import os
import sys
import time
from pathlib import Path

import adafruit_rfm9x
import board
import busio
import digitalio
import msgpack
import requests
from dotenv import load_dotenv
from loguru import logger
from msgpack.exceptions import ExtraData, FormatError, OutOfData, UnpackValueError

load_dotenv()
logger.remove()
log_dir: Path = Path().joinpath("logs")

logger.add(
    log_dir.joinpath("rfm_receiver_errors.log"),
    level="ERROR",
    rotation="500 MB",
    retention="30 days",
)

logger.add(
    log_dir.joinpath("rfm_receiver_info.log"),
    level="INFO",
    rotation="500 MB",
    retention="30 days",
)

logger.add(sys.stderr, level="INFO")


class LoraReceiver:
    def __init__(self, frequency: int = 915):
        """
        Initialize LoRa receiver

        :param frequency: Frequency in MHz
        """

        cs = digitalio.DigitalInOut(board.CE1)
        reset = digitalio.DigitalInOut(board.D25)
        spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)

        self.rfm9x = adafruit_rfm9x.RFM9x(spi, cs, reset, frequency)
        self.rfm9x.tx_power = 23
        self.rfm9x.spreading_factor = 7
        self.rfm9x.signal_bandwidth = 125000
        self.rfm9x.coding_rate = 5
        self.rfm9x.enable_crc = True
        self.rfm9x.receive_timeout = 5.0

    def receive_data(self):
        try:
            packet = self.rfm9x.receive(with_ack=True)
            if packet is not None:
                self._process_packet(packet=packet)
        except IOError as er:
            logger.error(f"Error receiving data: {er}")

    def _process_packet(self, packet: bytearray):
        try:
            packet_data = msgpack.unpackb(packet)
            sender_id: str = packet_data.get("sender_id", "")
            logger.info(f"Received packet from {sender_id}")
            prefix = sender_id.upper()
            device_id = os.getenv(f"{prefix}_DEVICE_ID", "")
            api_key = os.getenv(f"{prefix}_API_KEY", "")
            headers: dict = {
                "Content-Type": "application/json",
                "X-API-Key": api_key,
                "X-Device-Id": device_id,
            }
            if not device_id or not api_key:
                logger.error(f"No credentials found for sender_id '{sender_id}'")
                return
            self._post_data(
                sensor_data=packet_data.get("data", {}),
                headers=headers,
            )
        except (ExtraData, FormatError, OutOfData, UnpackValueError) as er:
            logger.error(f"Unpack error: {er}")

    @staticmethod
    def _post_data(sensor_data: dict, headers: dict[str, str]):
        url = str(os.getenv("API_URL"))
        post_data: dict = sensor_data.get("data", {})
        try:
            response = requests.post(url, json=post_data, headers=headers)
            response.raise_for_status()
            logger.info(f"Status Code: {response.status_code}")
        except requests.exceptions.RequestException as er:
            logger.error(f"An error occurred: {er}")


if __name__ == "__main__":
    receiver = LoraReceiver()
    logger.info("LoRa Receiver initialized. Waiting for messages...")

    while True:
        try:
            receiver.receive_data()
            time.sleep(0.1)
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            time.sleep(1)