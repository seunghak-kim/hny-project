from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime
from uuid import UUID 


# chatsession scheams 

class ChatSessionBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=20, description="채팅 세션 제목")
    
class ChatSessionCreate(ChatSessionBase):
    user_id : int = Field(..., description="사용자 ID")

class ChatSessionResponse(ChatSessionBase):
    id : UUID = Field(..., description="채팅 세션 ID")
    user_id : int = Field(..., description="사용자 ID")
    created_at : datetime = Field(..., description="생성일")
    updated_at : Optional[datetime] = Field(None, description="수정일")
    
    class Config:
        from_attributes = True 
        
# ChatMessage Schemas 

class ChatMessageBase(BaseModel):
    sender_type: str = Field(..., pattern=r'^(user|assistant)$', description="발신자 타입 (user/assistant)")
    content: str = Field(..., min_length=1, description="메시지 내용")
    
    @field_validator('sender_type')
    def validate_sender_type(cls, v):
        if v not in ['user', 'assistant']:
            raise ValueError('sender_type must be either "user" or "assistant"')
        return v 

class ChatMessageCreate(ChatMessageBase):
    session_id:UUID = Field(..., description="세션 ID")
    
class ChatMessageResponse(ChatMessageBase):
    id:UUID = Field(..., description="메시지 ID")
    session_id:UUID = Field(..., description="세션 ID")
    created_at:datetime = Field(..., description="생성일")
    
    class Config:
        from_attributes = True 

class ChatSessionWithMessages(ChatSessionResponse):
    messages: list[ChatMessageResponse] = []
    
    class Config:
        from_attributes = True 
        