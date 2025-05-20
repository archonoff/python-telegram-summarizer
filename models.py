from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class TextEntity(BaseModel):
    type: str
    text: str


class ReactionUser(BaseModel):
    from_: str | None = Field(default=None, alias='from')
    from_id: str
    date: datetime


class Reaction(BaseModel):
    type: str
    count: int
    emoji: str
    recent: list[ReactionUser]


class BaseMessage(BaseModel):
    id: int
    type: str
    date: datetime
    date_unixtime: str
    text: str | list = ''
    text_entities: list[TextEntity] = []


class ServiceMessage(BaseMessage):
    actor: str | None = None
    actor_id: str | None = None
    action: str
    members: list[str | None] | None = None
    message_id: int | None = None
    title: str | None = None


class UserMessage(BaseMessage):
    from_: str | None = Field(default=None, alias='from')
    from_id: str | None = None
    edited: datetime | None = None
    edited_unixtime: str | None = None
    reply_to_message_id: int | None = None
    reactions: list[Reaction] | None = None

    @field_validator('text')
    @classmethod
    def process_text(cls, v):
        if isinstance(v, list):
            result = ''
            for item in v:
                if isinstance(item, str):
                    result += item
                elif isinstance(item, dict) and 'text' in item:
                    result += item['text']
            return result
        return v


class ChatHistory(BaseModel):
    name: str
    type: str
    id: int
    messages: list[ServiceMessage | UserMessage]

    @field_validator('messages', mode='before')
    @classmethod
    def parse_messages(cls, messages_data):
        result = []
        for msg in messages_data:
            if msg.get('type') == 'service':
                result.append(ServiceMessage.model_validate(msg))
            else:
                result.append(UserMessage.model_validate(msg))
        return result
