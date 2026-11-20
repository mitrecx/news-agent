"""模型配置的输入、公开状态和内部运行配置。"""

from urllib.parse import urlsplit
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator


class ModelSettingsInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=80)
    base_url: str = Field(min_length=1, max_length=2048)
    model: str = Field(min_length=1, max_length=200)
    api_key: SecretStr | None = None
    temperature: float = Field(default=0.7, ge=0, le=2)
    max_tokens: int = Field(default=2000, ge=64, le=65536)

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, value: str) -> str:
        parsed = urlsplit(value)
        if (
            parsed.scheme not in {"https", "http"}
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or any(char.isspace() for char in value)
        ):
            raise ValueError(
                "请输入完整的 HTTP(S) API 地址，不要包含账号、查询参数或片段"
            )
        if parsed.path.rstrip("/").endswith("/chat/completions"):
            raise ValueError("请填写 API 根地址（如 /v1），不要包含 /chat/completions")
        return value.rstrip("/")


class ModelSettingsPublic(BaseModel):
    id: UUID
    name: str
    base_url: str
    model: str
    has_api_key: bool
    temperature: float
    max_tokens: int
    is_active: bool


class ModelSettingsCollection(BaseModel):
    items: list[ModelSettingsPublic]
    active_id: UUID | None


class ModelProbeInput(ModelSettingsInput):
    profile_id: UUID | None = None


class ModelRuntime(BaseModel):
    base_url: str
    model: str
    api_key: SecretStr
    temperature: float
    max_tokens: int


class ModelTestResult(BaseModel):
    success: bool
    message: str
    latency_ms: int | None = None


class ModelListResult(BaseModel):
    models: list[str]
