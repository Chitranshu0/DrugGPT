"""FastAPI route modules (one view module per API domain).

Each module exposes ``make_router(service)`` which returns an ``APIRouter``
whose handlers close over the injected ``MedicalRAGService``. ``src.main``
assembles them into the application.
"""
