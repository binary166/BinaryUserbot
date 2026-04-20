"""
Глобальное изменяемое состояние юзербота.
Импортируется и изменяется из разных модулей.
"""
import asyncio
from config import MY_ID

message_store:     dict = {}
known_users:       set  = set()

ebalaj_active:     dict = {}
ebalaj_history:    dict = {}
troll_active:      dict = {}
troll_history:     dict = {}
muted_users:       dict = {}
animating_msgs:    set  = set()

auto_comment_text: str | None = None
eng_mode_active:   bool = False
premium_emoji_active: bool = True

ac_active:  dict = {}
ac_history: dict = {}

bw_words:   list = []
bw_chat_id: int  = 0

auto_comment_channels: dict = {}

is_afk:     bool = False
afk_reason: str  = "Нет на месте"
afk_time         = None

check_events:  dict = {}
check_results: dict = {}

logs_chat_id: int = MY_ID

ai_semaphore: asyncio.Semaphore | None = None
