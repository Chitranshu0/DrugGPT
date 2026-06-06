from typing import TypedDict

class MedicalState(TypedDict):
    question: str
    context: str
    answer: str