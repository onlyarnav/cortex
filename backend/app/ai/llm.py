from functools import lru_cache
from langchain_groq import ChatGroq
from app.core.config import settings
from app.core.logging import logger

MAX_CONTEXT_CHUNKS = 5

SYSTEM_PROMPT = (
    "You are Cortex, a knowledge assistant. Answer the question using ONLY "
    "the provided context. If the answer is not contained in the context, "
    "say \"I don't have enough information to answer that.\" Do not make "
    "up information."
)


@lru_cache
def get_llm() -> ChatGroq:
    return ChatGroq(
        api_key=settings.GROQ_API_KEY,
        model=settings.LLM_MODEL,
        temperature=0.2,
        timeout=30,
        max_retries=2,
    )


def build_prompt(question: str, context_chunks: list[str]) -> str:
    context = "\n\n---\n\n".join(context_chunks[:MAX_CONTEXT_CHUNKS])
    return (
        f"Context:\n{context}\n\n"
        f"Question: {question}\n\n"
        f"Answer:"
    )


def generate_answer(question: str, context_chunks: list[str]) -> str:
    if not context_chunks:
        return "I don't have enough information to answer that."

    llm = get_llm()
    prompt = build_prompt(question, context_chunks)

    try:
        response = llm.invoke([
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ])
        return response.content
    except Exception as e:
        logger.error(f"LLM generation failed: {e}", exc_info=True)
        raise