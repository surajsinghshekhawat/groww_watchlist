from pydantic import BaseModel, Field


class PushKeys(BaseModel):
    p256dh: str = Field(min_length=8, max_length=255)
    auth: str = Field(min_length=8, max_length=255)


class PushSubscribeRequest(BaseModel):
    endpoint: str = Field(min_length=10, max_length=2048)
    keys: PushKeys


class PushUnsubscribeRequest(BaseModel):
    endpoint: str = Field(min_length=10, max_length=2048)


class PushStatusResponse(BaseModel):
    configured: bool
    subscribed: bool
    subscription_count: int
