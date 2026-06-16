import os
import shutil
import sqlite3
import stat
import tempfile
from pathlib import Path

from telethon import TelegramClient
from telethon.sessions.sqlite import SQLiteSession
try:
    from telethon.tl.custom.message import Message as CustomMessage
except Exception:
    CustomMessage = None
from telethon.tl.patched import Message as PatchedMessage
from telethon.tl.types import PeerChannel, PeerChat, PeerUser

from config import SESSION_NAME, API_ID, API_HASH


BASE_DIR = Path(__file__).resolve().parent


def _make_writable(path: Path) -> None:
    try:
        current = path.stat().st_mode
        current |= stat.S_IRUSR | stat.S_IWUSR
        if path.is_dir():
            current |= stat.S_IXUSR
        os.chmod(path, current)
    except Exception:
        pass


def _session_file_for(base: Path) -> Path:
    return Path(f"{base}.session")


def _session_journal_for(base: Path) -> Path:
    return Path(f"{base}.session-journal")


def _is_readonly_sqlite_error(exc: BaseException) -> bool:
    return isinstance(exc, sqlite3.OperationalError) and "readonly" in str(exc).lower()


class ResilientSQLiteSession(SQLiteSession):
    def __init__(self, session_id=None, store_tmp_auth_key_on_disk: bool = False):
        self._binary_readonly_mode = False
        super().__init__(session_id=session_id, store_tmp_auth_key_on_disk=store_tmp_auth_key_on_disk)
        self.save_entities = False

    def _enter_readonly_mode(self, exc: BaseException) -> bool:
        if not _is_readonly_sqlite_error(exc):
            return False
        if not self._binary_readonly_mode:
            print(f"[session] readonly mode enabled for {self.filename}: {exc}")
        self._binary_readonly_mode = True
        self.save_entities = False
        return True

    def _update_session_table(self):
        if getattr(self, "_binary_readonly_mode", False):
            return
        try:
            return super()._update_session_table()
        except Exception as exc:
            if self._enter_readonly_mode(exc):
                return
            raise

    def set_update_state(self, entity_id, state):
        if self._binary_readonly_mode:
            return
        try:
            return super().set_update_state(entity_id, state)
        except Exception as exc:
            if self._enter_readonly_mode(exc):
                return
            raise

    def process_entities(self, tlo):
        if self._binary_readonly_mode or not self.save_entities:
            return
        try:
            return super().process_entities(tlo)
        except Exception as exc:
            if self._enter_readonly_mode(exc):
                return
            raise

    def save(self):
        if self._binary_readonly_mode:
            return
        try:
            return super().save()
        except Exception as exc:
            if self._enter_readonly_mode(exc):
                return
            raise

    def close(self):
        try:
            return super().close()
        except Exception as exc:
            if self._enter_readonly_mode(exc):
                return
            raise

    def _execute(self, stmt, *values):
        if self._binary_readonly_mode:
            command = (stmt or "").lstrip().split(None, 1)[0].lower()
            if command in {"insert", "update", "delete", "replace", "create", "alter", "drop"}:
                return None
        try:
            return super()._execute(stmt, *values)
        except Exception as exc:
            if self._enter_readonly_mode(exc):
                return None
            raise


def _runtime_session_dir() -> Path:
    candidates = [
        BASE_DIR / ".runtime",
        Path.home() / ".binaryuserbot_runtime",
        Path(tempfile.gettempdir()) / "binaryuserbot_runtime",
    ]
    for candidate in candidates:
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            _make_writable(candidate)
            probe = candidate / ".write_probe"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
            return candidate
        except Exception:
            continue
    return BASE_DIR


def _resolve_session_candidates(session_name: str) -> list[Path]:
    raw = Path(str(session_name))
    if raw.is_absolute():
        return [raw]

    ordered = [
        Path.cwd() / raw,
        BASE_DIR / raw,
        _runtime_session_dir() / raw.name,
    ]
    unique: list[Path] = []
    seen: set[str] = set()
    for candidate in ordered:
        key = str(candidate.resolve()) if candidate.exists() else str(candidate)
        if key in seen:
            continue
        seen.add(key)
        unique.append(candidate)
    return unique


def _probe_sqlite_write(base: Path) -> bool:
    session_file = _session_file_for(base)
    try:
        session_file.parent.mkdir(parents=True, exist_ok=True)
        _make_writable(session_file.parent)
        if session_file.exists():
            _make_writable(session_file)
        else:
            with open(session_file, "a+b"):
                pass
        conn = sqlite3.connect(str(session_file))
        try:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("ROLLBACK")
        finally:
            conn.close()
        return True
    except Exception:
        return False


def _copy_session_storage(src_base: Path, dst_base: Path) -> None:
    src_file = _session_file_for(src_base)
    dst_file = _session_file_for(dst_base)
    src_journal = _session_journal_for(src_base)
    dst_journal = _session_journal_for(dst_base)

    dst_file.parent.mkdir(parents=True, exist_ok=True)
    _make_writable(dst_file.parent)
    if src_file.exists() and not dst_file.exists():
        shutil.copy2(src_file, dst_file)
    if src_journal.exists() and not dst_journal.exists():
        shutil.copy2(src_journal, dst_journal)
    if dst_file.exists():
        _make_writable(dst_file)
    if dst_journal.exists():
        _make_writable(dst_journal)


def _select_session_base(session_name: str) -> Path:
    candidates = _resolve_session_candidates(session_name)
    existing = []
    for candidate in candidates:
        session_file = _session_file_for(candidate)
        journal_file = _session_journal_for(candidate)
        if candidate.exists() or session_file.exists() or journal_file.exists():
            existing.append(candidate)

    for candidate in existing:
        if _probe_sqlite_write(candidate):
            return candidate

    source = existing[0] if existing else candidates[0]
    runtime_base = _runtime_session_dir() / Path(str(session_name)).name
    if source != runtime_base:
        try:
            _copy_session_storage(source, runtime_base)
        except Exception:
            pass
    if _probe_sqlite_write(runtime_base):
        return runtime_base

    for candidate in candidates:
        if _probe_sqlite_write(candidate):
            return candidate
    return runtime_base


PRIMARY_SESSION_BASE = _select_session_base(SESSION_NAME)


def session_storage_paths() -> list[Path]:
    session_file = _session_file_for(PRIMARY_SESSION_BASE)
    journal_file = _session_journal_for(PRIMARY_SESSION_BASE)
    return [session_file, journal_file]


def ensure_runtime_permissions() -> None:
    checked: set[str] = set()
    paths = [
        BASE_DIR,
        PRIMARY_SESSION_BASE.parent,
        *session_storage_paths(),
        BASE_DIR / "settings.json",
        BASE_DIR / "notes.json",
    ]
    for path in paths:
        key = str(path)
        if key in checked:
            continue
        checked.add(key)
        if path.exists():
            _make_writable(path)


def _message_permalink(message) -> str | None:
    message_id = getattr(message, "id", None)
    peer = getattr(message, "peer_id", None)
    if not message_id or peer is None:
        return None

    chat = getattr(message, "_chat", None) or getattr(message, "chat", None)
    username = getattr(chat, "username", None)
    if username:
        return f"https://t.me/{username}/{message_id}"

    if isinstance(peer, PeerChannel):
        return f"https://t.me/c/{peer.channel_id}/{message_id}"
    if isinstance(peer, PeerChat):
        return f"tg://openmessage?chat_id={peer.chat_id}&message_id={message_id}"
    if isinstance(peer, PeerUser):
        return f"tg://openmessage?user_id={peer.user_id}&message_id={message_id}"
    return None


def _install_message_link_compatibility() -> None:
    for cls in (PatchedMessage, CustomMessage):
        if cls is None:
            continue
        existing = getattr(cls, "link", None)
        if not isinstance(existing, property):
            cls.link = property(_message_permalink)
        if not hasattr(cls, "get_link"):
            cls.get_link = _message_permalink


_install_message_link_compatibility()

ensure_runtime_permissions()

print(f"[session] using {PRIMARY_SESSION_BASE}")

client = TelegramClient(ResilientSQLiteSession(str(PRIMARY_SESSION_BASE)), API_ID, API_HASH)
client.session.save_entities = False
