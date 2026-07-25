import pytest
from unittest.mock import AsyncMock, MagicMock


class TestLLMServiceStreamChat:
    """Test that stream_chat yields plain text deltas (OpenAI SDK format)"""

    @pytest.mark.asyncio
    async def test_stream_chat_yields_text_deltas(self):
        """stream_chat should yield str chunks from OpenAI streaming API"""
        from app.services.llm_service import LLMService

        service = LLMService()
        service._initialized = True

        # Build mock chunks
        chunks = []
        for text in ["Hello", " World", "!"]:
            chunk = MagicMock()
            chunk.choices = [MagicMock()]
            chunk.choices[0].delta = MagicMock(content=text)
            chunks.append(chunk)

        # Create async iterator for the stream
        async def chunk_generator():
            for chunk in chunks:
                yield chunk

        # Mock: await client.chat.completions.create(stream=True) -> async iterable
        mock_stream = chunk_generator()
        service.client = MagicMock()
        service.client.chat = MagicMock()
        service.client.chat.completions = MagicMock()
        service.client.chat.completions.create = AsyncMock(return_value=mock_stream)

        # Collect all yielded values
        results = []
        async for delta in service.stream_chat("system", "user"):
            results.append(delta)

        assert results == ["Hello", " World", "!"]
        assert all(isinstance(r, str) for r in results)

    @pytest.mark.asyncio
    async def test_stream_chat_skips_none_content(self):
        """stream_chat should skip chunks with None content (e.g. role delta)"""
        from app.services.llm_service import LLMService

        service = LLMService()
        service._initialized = True

        chunks = []

        # First chunk often has role but no content
        chunk1 = MagicMock()
        chunk1.choices = [MagicMock()]
        chunk1.choices[0].delta = MagicMock(content=None)
        chunks.append(chunk1)

        for text in ["Hello"]:
            chunk = MagicMock()
            chunk.choices = [MagicMock()]
            chunk.choices[0].delta = MagicMock(content=text)
            chunks.append(chunk)

        async def chunk_generator():
            for chunk in chunks:
                yield chunk

        mock_stream = chunk_generator()
        service.client = MagicMock()
        service.client.chat = MagicMock()
        service.client.chat.completions = MagicMock()
        service.client.chat.completions.create = AsyncMock(return_value=mock_stream)

        results = []
        async for delta in service.stream_chat("system", "user"):
            results.append(delta)

        assert results == ["Hello"]