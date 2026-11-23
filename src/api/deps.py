"""Small helpers shared by the route modules."""

from fastapi import HTTPException


def get_or_404(action):
    """Run a store lookup, turning a missing record into an HTTP 404."""
    try:
        return action()
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
