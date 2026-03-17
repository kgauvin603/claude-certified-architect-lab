from pathlib import Path

from .schemas import TicketContext


SESSION_DIR = Path("data/sessions")
SESSION_DIR.mkdir(parents=True, exist_ok=True)


def session_path(session_id: str) -> Path:
    return SESSION_DIR / f"{session_id}.json"


def save_session(ctx: TicketContext) -> None:
    session_path(ctx.session_id).write_text(ctx.model_dump_json(indent=2), encoding="utf-8")


def load_session(session_id: str) -> TicketContext | None:
    path = session_path(session_id)
    if not path.exists():
        return None
    return TicketContext.model_validate_json(path.read_text(encoding="utf-8"))
