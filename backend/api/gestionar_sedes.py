"""
Compatibility shim for the previous Spanish module `gestionar_sedes`.

This file keeps the old import path working for external imports.
New implementation lives in `backend.api.room_mgmt` (see `create_room` / `/api/rooms`).
"""

from backend.api.room_mgmt import (
    router as router,
    create_room as crear_sede,  # keep Spanish alias
    create_room_endpoint as crear_sede_endpoint,
)

__all__ = ["router", "crear_sede", "crear_sede_endpoint"]
