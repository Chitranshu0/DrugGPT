"""Tiny script to check that the Groq LLM connection works.

Run from the project root:

    python -m scripts.smoke_test_llm
"""

from backend.rag.generation import llm


def main():
    response = llm.invoke("Reply with one short sentence: hello from DrugGPT.")
    print(response.content)


if __name__ == "__main__":
    main()
