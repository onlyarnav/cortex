from langchain_groq import ChatGroq
from app.core.config import settings

llm = ChatGroq(
    api_key=settings.GROQ_API_KEY,
    model="openai/gpt-oss-120b",
    temperature=0.2
)

def generate_answer(question: str, context_chunks: list[str]) -> str:
    context = "\n\n".join(context_chunks)

    prompt = f"""Answer the question using ONLY the context below. If the answer isn't in the context, say "I don't have enough information to answer that."

Context:
{context}

Question: {question}

Answer:"""

    response = llm.invoke(prompt)
    return response.content