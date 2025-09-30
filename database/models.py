from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database.db import Base

class BaseModel(Base):
    __abstract__ = True

    def __str__(self):
        fields = ", ".join(f"{k}={getattr(self, k)}" for k in self.__table__.columns.keys())
        return f"<{self.__class__.__name__}({fields})>"

class Lead(BaseModel):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    phone = Column(String, nullable=False, unique=True)
    client_type = Column(String, nullable=True)
    preferred_channel = Column(String, nullable=True)
    next_action_time = Column(DateTime, nullable=True)
    pending_action = Column(String, nullable=True)
    extra_data = Column(JSON, nullable=True)

    conversations = relationship(
        "Conversation", back_populates="lead", cascade="all, delete-orphan"
    )

class Conversation(BaseModel):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="CASCADE"))
    message = Column(String, nullable=False)
    channel = Column(String, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    embedding_id = Column(String, nullable=True)  # store Chroma vector reference

    lead = relationship("Lead", back_populates="conversations")

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String)