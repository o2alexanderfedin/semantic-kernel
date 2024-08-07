# Copyright (c) Microsoft. All rights reserved.

from unittest.mock import patch

import pytest
from numpy import array

from semantic_kernel.connectors.ai.ollama.services.ollama_text_embedding import OllamaTextEmbedding
from tests.unit.connectors.ollama.utils import MockResponse


@pytest.mark.asyncio
@patch("aiohttp.ClientSession.post")
async def test_embedding(mock_post):
    mock_post.return_value = MockResponse(response={"embedding": [0.1, 0.2, 0.3]})
    ollama = OllamaTextEmbedding(ai_model_id="test_model")
    response = await ollama.generate_embeddings(
        ["test_prompt"],
    )
    assert response.all() == array([0.1, 0.2, 0.3]).all()
    mock_post.assert_called_once_with(
        "http://localhost:11434/api/embeddings",
        json={
            "model": "test_model",
            "prompt": "test_prompt",
            "options": {},
        },
    )
