# # One job only: (OF THE clarifierAgent)
# # Takes vague question + memory context
# #         ↓
# # Rewrites it into a clear specific question
# #         ↓
# # Returns the clarified question


# # Entire agent flow 
# User Question (vague)
#         ↓
# Orchestrator
#         ↓
# Memory Agent → gets context
#         ↓
# Clarifier Agent → rewrites question using context
#         ↓
# Analysis Agent → gets a clear specific question
#         ↓
# Drive Agent → uploads chart if generated


import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def clarify_question(question: str, memory_context: str, callback=None) -> str:
    """
    Takes a vague question and memory context
    and rewrites it into a clear specific question.
    Returns the clarified question.
    """
    def emit(msg: str):
        if callback:
            callback(msg)
        else:
            print(msg)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=100,
        messages=[
            {
                "role": "system",
                "content": """You are a question clarifier for a data analysis system.
Your job is to rewrite vague or ambiguous questions into clear, specific questions.
Use the memory context to resolve pronouns like 'it', 'that', 'this', 'they' etc.

Rules:
- If the question is already clear and specific → return it unchanged
- If the question has pronouns or vague references → rewrite it using context
- Keep the rewritten question short and direct
- Never answer the question — only rewrite it
- Return ONLY the rewritten question, nothing else"""
            },
            {
                "role": "user",
                "content": f"""Memory context:
{memory_context}

User question:
{question}

Rewrite this question to be clear and specific:"""
            }
        ]
    )

    clarified = response.choices[0].message.content.strip()

    # if clarifier changed the question, show it
    if clarified.lower() != question.lower():
        emit(f"💡 Clarified: '{question}' → '{clarified}'")

    return clarified


def is_vague(question: str) -> bool:
    vague_words = [
        "it", "that", "this", "they", "them",
        "its", "their", "those", "these",
        "the same", "the one", "do it", "show it"
    ]
    # remove punctuation before checking
    import re
    question_clean = re.sub(r'[^\w\s]', ' ', question.lower())
    for word in vague_words:
        if f" {word} " in f" {question_clean} ":
            return True
    return False