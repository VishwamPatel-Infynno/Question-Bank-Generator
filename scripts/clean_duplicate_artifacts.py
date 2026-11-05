import asyncio
import logging

from app.db.session import async_session_factory
from app.models.question import QuestionModel
from sqlalchemy import delete, select

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def cleanup_discarded_duplicates() -> int:
    """Permanently purges existing discarded duplicate questions from PostgreSQL."""
    async with async_session_factory() as session:
        # Find all questions with status 'discarded'
        stmt_select = select(QuestionModel.id).where(QuestionModel.status == "discarded")
        res = await session.execute(stmt_select)
        ids_to_delete = res.scalars().all()

        if not ids_to_delete:
            logger.info("No discarded duplicate questions found in database.")
            return 0

        stmt_del = delete(QuestionModel).where(QuestionModel.id.in_(ids_to_delete))
        res_del = await session.execute(stmt_del)
        await session.commit()
        count = res_del.rowcount or 0
        logger.info(
            "Successfully purged %s discarded duplicate question(s) from database: %s",
            count,
            ids_to_delete,
        )
        return count


if __name__ == "__main__":
    count = asyncio.run(cleanup_discarded_duplicates())
    print(f"Purged {count} discarded duplicate question(s).")
