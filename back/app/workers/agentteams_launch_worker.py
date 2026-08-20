"""Durable AgentTeams launch dispatcher and reconciliation worker."""

import asyncio
import logging

from app.core.database import async_session_factory, engine
from app.services.agentteams_launch_intent_service import AgentTeamsLaunchIntentService


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run_worker(poll_seconds: float = 2.0) -> None:
    logger.info("AgentTeams launch worker started")
    try:
        while True:
            try:
                async with async_session_factory() as session:
                    processed = await AgentTeamsLaunchIntentService(
                        session
                    ).process_available()
                if processed:
                    logger.info("AgentTeams launch worker processed intents: %s", processed)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("AgentTeams launch worker iteration failed")
            await asyncio.sleep(poll_seconds)
    finally:
        await engine.dispose()


def main() -> None:
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
