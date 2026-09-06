from pydantic import BaseModel, Field


class SettingsResponse(BaseModel):
    sensitivity: str
    display_name: str
    email: str


class SettingsUpdate(BaseModel):
    sensitivity: str = Field(pattern="^(LOW|MEDIUM|HIGH)$")
