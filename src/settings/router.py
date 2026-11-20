"""用户模型列表、启用与连接测试；密钥不会返回到页面。"""

import asyncio
import time
from typing import Annotated
from uuid import UUID

import httpx
from asyncpg import Connection
from fastapi import APIRouter, Depends, HTTPException
from langchain_openai import ChatOpenAI

from ..auth.database import get_db
from ..auth.models import User
from ..auth.router import get_current_user
from .models import (
    ModelListResult,
    ModelProbeInput,
    ModelSettingsCollection,
    ModelSettingsInput,
    ModelSettingsPublic,
    ModelTestResult,
)
from .service import ModelSettingsService

AuthenticatedUser = Annotated[User, Depends(get_current_user)]
DatabaseConnection = Annotated[Connection, Depends(get_db)]

router = APIRouter(prefix="/api/settings/models", tags=["settings"])


async def run_operation(operation):
    try:
        return await operation
    except LookupError:
        raise HTTPException(404, detail="模型配置不存在") from None
    except ValueError as error:
        raise HTTPException(400, detail=str(error)) from None


@router.get("", response_model=ModelSettingsCollection)
async def read_models(current_user: AuthenticatedUser, conn: DatabaseConnection):
    return await ModelSettingsService.read(conn, current_user.id)


@router.post("", response_model=ModelSettingsPublic, status_code=201)
async def create_model(
    data: ModelSettingsInput, current_user: AuthenticatedUser, conn: DatabaseConnection
):
    return await run_operation(ModelSettingsService.create(conn, current_user.id, data))


async def check_connection(runtime):
    start = time.monotonic()
    try:
        llm = ChatOpenAI(
            model=runtime.model,
            base_url=runtime.base_url,
            api_key=runtime.api_key.get_secret_value(),
            temperature=runtime.temperature,
            max_tokens=16,
            timeout=20,
            max_retries=0,
        )
        result = await asyncio.wait_for(llm.ainvoke("请只回复：连接成功"), timeout=22)
        if not result.content:
            return ModelTestResult(
                success=False, message="接口已连接，但模型没有返回文本，请检查模型名称"
            )
        return ModelTestResult(
            success=True,
            message="模型连接正常",
            latency_ms=int((time.monotonic() - start) * 1000),
        )
    except Exception as error:  # noqa: BLE001 -- 服务商异常可能含密钥，仅返回安全诊断
        messages = {
            401: "API Key 无效或已过期",
            403: "该 API Key 没有模型访问权限",
            404: "API 地址或模型名称不存在",
            429: "请求过于频繁或额度不足",
        }
        return ModelTestResult(
            success=False,
            message=messages.get(
                getattr(error, "status_code", None),
                "连接失败，请检查 API 地址、模型名称和网络",
            ),
        )


@router.post("/test", response_model=ModelTestResult)
async def test_draft(
    data: ModelProbeInput, current_user: AuthenticatedUser, conn: DatabaseConnection
):
    runtime = await run_operation(
        ModelSettingsService.prepare(conn, current_user.id, data, data.profile_id)
    )
    return await check_connection(runtime)


@router.post("/available", response_model=ModelListResult)
async def list_available_models(
    data: ModelProbeInput, current_user: AuthenticatedUser, conn: DatabaseConnection
):
    runtime = await run_operation(
        ModelSettingsService.prepare(conn, current_user.id, data, data.profile_id)
    )
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=False) as client:
            response = await client.get(
                runtime.base_url + "/models",
                headers={
                    "Authorization": f"Bearer {runtime.api_key.get_secret_value()}"
                },
            )
            response.raise_for_status()
            items = response.json().get("data", [])
        return ModelListResult(
            models=sorted(
                {
                    item["id"]
                    for item in items
                    if isinstance(item, dict) and isinstance(item.get("id"), str)
                }
            )
        )
    except Exception:  # noqa: BLE001 -- 不向前端暴露服务商响应或私有连接地址
        raise HTTPException(
            400, detail="无法获取模型列表，可以手动填写模型名称并测试连接"
        ) from None


@router.put("/{profile_id}", response_model=ModelSettingsPublic)
async def update_model(
    profile_id: UUID,
    data: ModelSettingsInput,
    current_user: AuthenticatedUser,
    conn: DatabaseConnection,
):
    return await run_operation(
        ModelSettingsService.update(conn, current_user.id, profile_id, data)
    )


@router.post("/{profile_id}/activate", response_model=ModelSettingsCollection)
async def activate_model(
    profile_id: UUID, current_user: AuthenticatedUser, conn: DatabaseConnection
):
    return await run_operation(
        ModelSettingsService.activate(conn, current_user.id, profile_id)
    )


@router.delete("/{profile_id}", response_model=ModelSettingsCollection)
async def delete_model(
    profile_id: UUID, current_user: AuthenticatedUser, conn: DatabaseConnection
):
    return await run_operation(
        ModelSettingsService.delete(conn, current_user.id, profile_id)
    )


@router.post("/{profile_id}/test", response_model=ModelTestResult)
async def test_saved_model(
    profile_id: UUID, current_user: AuthenticatedUser, conn: DatabaseConnection
):
    runtime = await run_operation(
        ModelSettingsService.resolve_profile(conn, current_user.id, profile_id)
    )
    return await check_connection(runtime)
