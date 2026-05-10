import sys
import time

from pathlib import Path

import adafruit_rfm9x
import board
import busio
import digitalio
import httpx
import msgpack

from loguru import logger
from msgpack.exceptions import ExtraData, FormatError, OutOfData, UnpackValueError
from pydantic_settings import BaseSettings, SettingsConfigDict
from tenacity import retry, stop_after_attempt, wait_exponential

POLL_INTERVAL = 0.1


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="allow")

    api_url: str

    def get_credentials(self, device_num: int) -> tuple[str, str]:
        extras = self.model_extra or {}
        device_id = extras.get(f"device_{device_num}_device_id", "")
        api_key = extras.get(f"device_{device_num}_api_key", "")
        if not device_id or not api_key:
            raise ValueError(
                f"No credentials for device {device_num} — "
                f"set DEVICE_{device_num}_DEVICE_ID and DEVICE_{device_num}_API_KEY in .env"
            )
        return device_id, api_key


def _log_retry(retry_state) -> None:
    logger.warning(
        f"POST failed (attempt {retry_state.attempt_number}): {retry_state.outcome.exception()}"
    )


class LoraReceiver:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.http = httpx.Client(timeout=10.0)

        cs = digitalio.DigitalInOut(board.CE1)
        reset = digitalio.DigitalInOut(board.D25)
        spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)

        self.radio = adafruit_rfm9x.RFM9x(spi, cs, reset, 915.0)
        self.radio.tx_power = 23
        self.radio.spreading_factor = 7
        self.radio.signal_bandwidth = 125000
        self.radio.coding_rate = 5
        self.radio.enable_crc = True
        self.radio.receive_timeout = 5.0

    def run(self) -> None:
        logger.info("Listening on 915 MHz...")
        try:
            while True:
                try:
                    self._poll()
                    time.sleep(POLL_INTERVAL)
                except Exception as exc:
                    logger.error(f"Poll error: {exc}")
                    time.sleep(1.0)
        except KeyboardInterrupt:
            pass
        finally:
            self.http.close()

    def _poll(self) -> None:
        packet = self.radio.receive(with_ack=True)
        if packet is None:
            return

        try:
            packet_data = msgpack.unpackb(bytes(packet), raw=False)
        except (ExtraData, FormatError, OutOfData, UnpackValueError) as exc:
            logger.warning(f"Bad packet: {exc}")
            return

        device_num: int = packet_data.get("device_num")
        data: dict = packet_data.get("data", {})

        if device_num is None:
            logger.warning("Packet missing device_num, dropping")
            return

        logger.info(f"device={device_num} rssi={self.radio.last_rssi}dBm")

        try:
            device_id, api_key = self.settings.get_credentials(device_num)
        except ValueError as exc:
            logger.error(str(exc))
            return

        try:
            self._post(data, device_id, api_key)
        except Exception as exc:
            logger.error(f"POST failed after retries: {exc}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        before_sleep=_log_retry,
        reraise=True,
    )
    def _post(self, data: dict, device_id: str, api_key: str) -> None:
        response = self.http.post(
            self.settings.api_url,
            json=data,
            headers={"X-API-Key": api_key, "X-Device-Id": device_id},
        )
        response.raise_for_status()
        logger.info(f"Posted → HTTP {response.status_code}")


def main() -> None:
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    logger.remove()
    logger.add(log_dir / "receiver.log", level="INFO", rotation="500 MB", retention="30 days")
    logger.add(log_dir / "receiver_errors.log", level="ERROR", rotation="500 MB", retention="30 days")
    logger.add(sys.stderr, level="INFO")

    settings = Settings()
    LoraReceiver(settings).run()


if __name__ == "__main__":
    main()
