from pydantic_settings import BaseSettings, SettingsConfigDict


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


settings = Settings()
