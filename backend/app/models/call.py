from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class CallSession(Base):
    __tablename__ = 'call_sessions'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    twilio_call_sid: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    from_number: Mapped[str | None] = mapped_column(String(50), index=True)
    to_number: Mapped[str | None] = mapped_column(String(50))
    call_status: Mapped[str | None] = mapped_column(String(50), index=True)
    direction: Mapped[str | None] = mapped_column(String(50))
    ai_session_id: Mapped[str | None] = mapped_column(String(255), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    transcripts: Mapped[list['TranscriptEntry']] = relationship(
        back_populates='call_session',
        cascade='all, delete-orphan',
    )


class TranscriptEntry(Base):
    __tablename__ = 'transcript_entries'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    call_session_id: Mapped[int] = mapped_column(ForeignKey('call_sessions.id'), nullable=False, index=True)
    speaker: Mapped[str] = mapped_column(String(50), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    call_session: Mapped[CallSession] = relationship(back_populates='transcripts')
