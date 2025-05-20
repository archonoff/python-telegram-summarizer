from datetime import datetime
from typing import List, Optional, Union, Any

from pydantic import BaseModel, Field, field_validator


class TextEntity(BaseModel):
    type: str
    text: str


class ReactionUser(BaseModel):
    from_: str = Field(alias='from')
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
    text: Union[str, list[Any]] = ""
    text_entities: list[TextEntity] = []


class ServiceMessage(BaseMessage):
    actor: Optional[str] = None
    actor_id: Optional[str] = None
    action: str
    members: Optional[List[Optional[str]]] = None
    message_id: Optional[int] = None
    title: Optional[str] = None


class UserMessage(BaseMessage):
    from_: Optional[str] = Field(default=None, alias='from')
    from_id: Optional[str] = None
    edited: Optional[datetime] = None
    edited_unixtime: Optional[str] = None
    reply_to_message_id: Optional[int] = None
    reactions: Optional[List[Reaction]] = None

    @field_validator('text')
    @classmethod
    def process_text(cls, v):
        if isinstance(v, list):
            result = ""
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
