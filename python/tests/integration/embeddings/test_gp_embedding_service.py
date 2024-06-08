# Copyright (c) Microsoft. All rights reserved.

import os
import sys

import pytest

import semantic_kernel as sk
import semantic_kernel.connectors.ai.google_palm as sk_gp
from semantic_kernel.core_plugins.text_memory_plugin import TextMemoryPlugin
from semantic_kernel.kernel import Kernel
from semantic_kernel.memory.semantic_text_memory import SemanticTextMemory

pytestmark = [
    pytest.mark.skipif(sys.version_info < (3, 9), reason="Google Palm requires Python 3.9 or greater"),
    pytest.mark.skipif(
        "Python_Integration_Tests" in os.environ,
        reason="Google Palm integration tests are only set up to run locally",
    ),
]


@pytest.mark.asyncio
async def test_gp_embedding_service(kernel: Kernel):
    palm_text_embed = sk_gp.GooglePalmTextEmbedding("models/embedding-gecko-001")
    kernel.add_service(palm_text_embed)

    memory = SemanticTextMemory(storage=sk.memory.VolatileMemoryStore(), embeddings_generator=palm_text_embed)
    kernel.add_plugin(TextMemoryPlugin(memory), "TextMemoryPlugin")

    await memory.save_information(collection="generic", id="info1", text="My budget for 2024 is $100,000")
    await memory.save_reference(
        "test",
        external_id="info1",
        text="this is a test",
        external_source_name="external source",
    )
