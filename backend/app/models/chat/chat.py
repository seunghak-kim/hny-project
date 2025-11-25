from sqlalchemy import (
    Column, 
    Integer,
    String,
    Boolean,
    TIMESTAMP,
    ForeignKey,
    UUID,
    Text
)

from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from app.db.postgre_db import Base
from sqlalchemy.orm import relationship
import uuid 

class ChatSession(Base):
    """
    Chat Session Model

    Represents a chat session between a user and the chat system.
    """
    __tablename__ = "chat_sessions"

    session_id = Column(
        String(100),
        primary_key=True,
        comment="Unique identifier for the chat session"
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ID of the user who owns the chat session"
    )
   
    title = Column(
        String(200),
        nullable=False,
        default="New Chat",
        comment="Title of the chat session"
    )

    last_message = Column(Text, comment="Preview of the last message in the session")
    message_count = Column(Integer, default=0, comment="Number of messages in the session")
    is_active = Column(Boolean, default=True, comment="Indicates if the session is active")
    metadata = Column(JSONB, comment="Metadata associated with the chat session")
    created_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Timestamp when the session was created"
        )
    updated_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Timestamp when the session was last updated"
    )
    
class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id = Column(Integer, primary_key=True, index= True)
    seesion_id = Column(String(100), ForeignKey("chat_sessions.session_id"), index=True)
    role = Column(String(20) , nullable=False, comment="Role of the message sender (e.g., user, system, bot)")    
    content = Column(Text, nullable=False, comment="Content of the chat message")
    structured_data = Column(JSONB, comment="Structured data associated with the message")
    created_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Timestamp when the message was created"
    )