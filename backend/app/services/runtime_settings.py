from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from app.models import RuntimeSettings, RuntimeSettingsUpdate


class RuntimeSettingsService:
    def __init__(self, file_path: Path) -> None:
        self.file_path = file_path
        self._settings = RuntimeSettings()

    def load(self) -> RuntimeSettings:
        if not self.file_path.exists():
            return self._settings
        try:
            data = json.loads(self.file_path.read_text(encoding="utf-8"))
            self._settings = RuntimeSettings.model_validate(data)
        except (json.JSONDecodeError, OSError, ValueError) as e:
            import logging

            logging.getLogger(__name__).warning(
                "无法读取或解析运行时配置 %s: %s — 使用内存默认直至修复该文件",
                self.file_path,
                e,
            )
        return self._settings

    def get(self) -> RuntimeSettings:
        return self._settings

    def update(self, payload: RuntimeSettingsUpdate) -> RuntimeSettings:
        current = self._settings.model_dump()
        for key, value in payload.model_dump(exclude_none=True).items():
            current[key] = value
        current["updated_at"] = datetime.utcnow().isoformat()
        self._settings = RuntimeSettings.model_validate(current)
        self._persist()
        return self._settings

    def _persist(self) -> None:
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.file_path.write_text(
            self._settings.model_dump_json(indent=2),
            encoding="utf-8",
        )

