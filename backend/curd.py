import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from database.models import Lead, LeadInteraction

async def get_lead(db: AsyncSession, lead_id: int):
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    return result.scalars().first()

async def get_last_interaction(db: AsyncSession, lead_id: int):
    result = await db.execute(
        select(LeadInteraction)
        .where(LeadInteraction.lead_id == lead_id)
        .order_by(LeadInteraction.timestamp.desc())
        .limit(1)
    )
    return result.scalars().first()



# async def insert_lead_interaction(db: AsyncSession, lead_id: int, conversation, duration):
#     """Inserts a lead interaction record into the database."""
#     async with db.begin():
#         interaction = LeadInteraction(
#             lead_id=lead_id,
#             interaction_type="Call",
#             call_duration=duration,
#             call_status="Answered",
#             conversation_history={"history": conversation},
#             ai_summary=" | ".join(conv.get("AI", "") for conv in conversation),
#             timestamp=datetime.datetime.utcnow(),
#         )
#         db.add(interaction)
#     await db.commit()

async def insert_lead_interaction(db: AsyncSession, lead_id: int, conversation, duration):
    """Inserts a lead interaction record into the database."""
    try:
        interaction = LeadInteraction(
            lead_id=lead_id,
            interaction_type="Call",
            call_duration=duration,
            call_status="Answered",
            conversation_history={"history": conversation},
            ai_summary=" | ".join(conv.get("AI", "") for conv in conversation),
            timestamp=datetime.datetime.utcnow(),
        )
        db.add(interaction)
        await db.commit()  # Explicitly commit

    except Exception as e:
        print(f"Error inserting lead interaction: {e}")
        await db.rollback()  # Ensure rollback on error

    finally:
        await db.close()  # Close session to prevent connection leaks

