from typing import Literal

from pydantic import BaseModel, Field


HostTransport = Literal["none", "http", "socket"]


class HostRecord(BaseModel):
    slug: str
    title: str
    transport: HostTransport = "none"
    runner_url: str = ""
    runner_socket_path: str = ""
    token_env_var: str = ""
    location: str = ""
    notes: str = ""
    updated_at: str = ""


class HostRunnerHealthRecord(BaseModel):
    status: str = "unknown"
    ok: bool = False
    checked_at: str = ""
    detail: str = ""
    endpoint: str = ""
    transport: str = "none"


class HostViewRecord(HostRecord):
    runner_health: HostRunnerHealthRecord = Field(default_factory=HostRunnerHealthRecord)


class HostUpsertRequest(BaseModel):
    slug: str = Field(min_length=1)
    title: str = Field(min_length=1)
    transport: HostTransport = "none"
    runner_url: str = ""
    runner_socket_path: str = ""
    token_env_var: str = ""
    location: str = ""
    notes: str = ""
