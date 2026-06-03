"""Tests for the RAG branch of the ChatOps agent (_answer_from_knowledge).

Covers the augment+generate half of the pipeline: retrieval is mocked via
rag_service, and the OpenRouter completion is mocked, so these run without a
vector DB or network. Async methods are driven with asyncio.run so no
pytest-asyncio plugin is required.
"""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.llm_agent import CloudAgentService, get_openai_tools


def _completion(text: str):
    """Build an object shaped like an OpenAI ChatCompletion with one message."""
    message = SimpleNamespace(content=text, tool_calls=None)
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def test_knowledge_tool_is_registered():
    names = {t["function"]["name"] for t in get_openai_tools()}
    assert "search_knowledge_base" in names


def test_blank_query_short_circuits():
    agent = CloudAgentService()
    result = asyncio.run(agent._answer_from_knowledge("   "))
    assert result["execution_status"] == "conversational"


def test_unavailable_knowledge_base():
    agent = CloudAgentService()
    with patch("app.services.llm_agent.rag_service.is_available", return_value=False):
        result = asyncio.run(agent._answer_from_knowledge("what is a golden image?"))
    assert result["execution_status"] == "unavailable"
    assert "upload" in result["response"].lower()


def test_no_results_returns_no_results_status():
    agent = CloudAgentService()
    with patch("app.services.llm_agent.rag_service.is_available", return_value=True), \
         patch("app.services.llm_agent.rag_service.search", return_value=[]):
        result = asyncio.run(agent._answer_from_knowledge("obscure question"))
    assert result["execution_status"] == "no_results"
    assert result["data"] == []


def test_search_failure_is_distinct_from_no_results():
    from app.services.rag_service import RagError

    agent = CloudAgentService()
    with patch("app.services.llm_agent.rag_service.is_available", return_value=True), \
         patch("app.services.llm_agent.rag_service.search", side_effect=RagError("index broken")):
        result = asyncio.run(agent._answer_from_knowledge("anything"))
    # A real failure must NOT be reported as an empty knowledge base.
    assert result["execution_status"] == "failed"
    assert "couldn't find" not in result["response"].lower()


def test_grounded_answer_uses_retrieved_context_and_cites_sources():
    agent = CloudAgentService()
    # Stub the OpenRouter client so synthesis returns a deterministic answer.
    agent.client = MagicMock()
    agent.client.chat.completions.create = AsyncMock(
        return_value=_completion("A golden image is a pre-baked VM template.")
    )

    matches = [
        {"content": "Golden images are pre-baked templates.", "source": "proxmox.pdf", "distance": 0.1},
        {"content": "They speed up provisioning.", "source": "proxmox.pdf", "distance": 0.2},
    ]
    with patch("app.services.llm_agent.rag_service.is_available", return_value=True), \
         patch("app.services.llm_agent.rag_service.search", return_value=matches):
        result = asyncio.run(agent._answer_from_knowledge("what is a golden image?"))

    assert result["execution_status"] == "knowledge"
    assert result["tool_called"] == "search_knowledge_base"
    assert result["data"] == ["proxmox.pdf"]  # deduped, sorted sources
    assert "golden image" in result["response"].lower()

    # The retrieved chunks must be injected into the synthesis system prompt.
    call_messages = agent.client.chat.completions.create.call_args.kwargs["messages"]
    system_prompt = call_messages[0]["content"]
    assert "Golden images are pre-baked templates." in system_prompt


def test_synthesis_failure_is_handled():
    agent = CloudAgentService()
    agent.client = MagicMock()
    agent.client.chat.completions.create = AsyncMock(side_effect=RuntimeError("LLM down"))

    matches = [{"content": "ctx", "source": "x.pdf", "distance": 0.1}]
    with patch("app.services.llm_agent.rag_service.is_available", return_value=True), \
         patch("app.services.llm_agent.rag_service.search", return_value=matches):
        result = asyncio.run(agent._answer_from_knowledge("question"))

    assert result["execution_status"] == "failed"
    assert result["data"] == ["x.pdf"]
