from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Float, Enum, DateTime, ForeignKey, JSON, Boolean
)
from sqlalchemy.orm import relationship
from .db_setup import Base


class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    phone_number = Column(String(20), nullable=True)
    email = Column(String(255), nullable=True)
    company = Column(String(255), nullable=True)
    industry = Column(String(255), nullable=True)
    contected = Column(Boolean, default=True)  # Fixed Boolean column

    # Relationship to interactions
    interactions = relationship("LeadInteraction", back_populates="lead")


class LeadInteraction(Base):
    __tablename__ = "lead_interactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False)

    interaction_type = Column(Enum("Call", "SMS", "Email", "Whatsapp", name="interaction_types"), nullable=False)
    channel = Column(String(50), nullable=True)

    # Call & Message status
    call_duration = Column(Float, nullable=True)
    call_status = Column(Enum("Answered", "Missed", "Declined", "Voicemail", name="call_status_types"), nullable=True)
    message_status = Column(Enum("Sent", "Opened", "Replied", "Failed", name="message_status_types"), nullable=True)
    recording_url = Column(String(255), nullable=True)

    # Complete conversation history
    conversation_history = Column(JSON, nullable=True)

    # AI-generated insights
    ai_summary = Column(Text, nullable=True)
    detected_emotion = Column(Enum("Happy", "Angry", "Neutral", "Frustrated", name="emotion_types"), nullable=True)

    # Feedback
    feedback_rating = Column(Integer, nullable=True)
    feedback_comment = Column(Text, nullable=True)

    timestamp = Column(DateTime, default=datetime.utcnow)

    # Relationship
    lead = relationship("Lead", back_populates="interactions")



class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String)
