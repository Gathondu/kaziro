"""Clear asyncio-loop-bound singletons after a Celery ``asyncio.run`` finishes.

Each :func:`backend.tasks.async_runner.run_sqlalchemy_async` call creates a new
event loop and closes it in ``finally``. Module-level LangChain / OpenRouter /
httpx clients created on a previous loop must be dropped or the next task hits
``RuntimeError: Event loop is closed``.
"""

from __future__ import annotations


def reset_loop_bound_clients() -> None:
    """Reset cached LLM / HTTP clients used from Celery async tasks."""
    from backend.agents import document_agent, evaluator_agent, parser_agent, research_agent
    from backend.services import rapidapi_query_builder

    rapidapi_query_builder.reset_structured_model()
    parser_agent.set_llm_for_tests(None)
    parser_agent.set_embedder_for_tests(None)
    evaluator_agent.set_llm_for_tests(None)
    research_agent.set_llm_for_tests(None)
    research_agent.set_firecrawl_client_for_tests(None)
    document_agent.set_llm_for_tests(None)
    document_agent.set_pdf_renderer_for_tests(None)


__all__ = ["reset_loop_bound_clients"]
