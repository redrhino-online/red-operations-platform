"""RED application factory composing RED with the pinned OpenExecutive shell.

ADR 0008: the application is this repository; OpenExecutive is a pinned
dependency vendored under ``vendor/openexecutive`` and reused through
composition, not copied and not edited. The factory builds a RED FastAPI app,
includes RED's own routes, and mounts the reused OpenExecutive ASGI app at
``/openexecutive`` so its shell, orchestrator and routes stay one dependency
hop away and remain cheap to update from upstream.

The OpenExecutive import is deferred into the factory so importing RED's routes
(or the pure domain) never drags in the vendored package or its heavy optional
dependencies. Mounting does not run the reused app's lifespan; the RED app's
dependencies run only when the mounted shell is actually exercised.
"""

from __future__ import annotations

from fastapi import FastAPI

from redops.api.routes import router as red_router

OPENEXECUTIVE_MOUNT_PATH = "/openexecutive"


def create_app() -> FastAPI:
    """Build the RED app and compose the reused OpenExecutive shell."""

    from openexecutive.api.main import app as openexecutive_app

    app = FastAPI(title="RED Operations Platform", version="0.1.0")
    app.include_router(red_router)
    app.mount(OPENEXECUTIVE_MOUNT_PATH, openexecutive_app)
    return app


app = create_app()
