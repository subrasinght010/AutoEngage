from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from .models import Lead, Conversation
from tools.vector_store import add_embedding , query_embeddings  # our Chroma helper

class DBManager:
    def __init__(self, session: AsyncSession):
        self.session = session

    # -----------------------------
    # Lead CRUD
    # -----------------------------
    async def add_lead(self, name: str, email: str, phone: str, client_type=None):
        lead = Lead(name=name, email=email, phone=phone, client_type=client_type)
        self.session.add(lead)
        await self.session.commit()
        await self.session.refresh(lead)
        return lead

    async def get_lead_by_id(self, lead_id: int):
        result = await self.session.execute(select(Lead).filter_by(id=lead_id))
        return result.scalar_one_or_none()

    async def get_lead_by_email(self, email: str):
        result = await self.session.execute(select(Lead).filter_by(email=email))
        return result.scalar_one_or_none()

    # -----------------------------
    # Conversation CRUD
    # -----------------------------
    async def add_conversation(self, lead_id: int, message: str, channel: str, use_embedding: bool = True):
        """
        Add conversation to SQLite and optionally save embedding to Chroma.
        """
        embedding_id = None

        if use_embedding:
            embedding_vector = query_embeddings(message)  # get vector representation
            embedding_id = f"conv_{lead_id}_{int(await self._get_next_conv_index(lead_id))}"
            add_embedding(embedding_id, lead_id, message, embedding_vector)

        conv = Conversation(
            lead_id=lead_id,
            message=message,
            channel=channel,
            embedding_id=embedding_id
        )
        self.session.add(conv)
        await self.session.commit()
        await self.session.refresh(conv)
        return conv


    async def get_conversations_by_lead(self, lead_id: int):
        result = await self.session.execute(select(Conversation).filter_by(lead_id=lead_id))
        return result.scalars().all()

    # -----------------------------
    # Helper
    # -----------------------------
    async def _get_next_conv_index(self, lead_id: int):
        """
        Returns next conversation index for embedding_id generation.
        """
        result = await self.session.execute(
            select(Conversation).filter_by(lead_id=lead_id)
        )
        convs = result.scalars().all()
        return len(convs) + 1
