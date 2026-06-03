import state

PE_TABLE = {
    "user":    ("5373012449597335010", "👤"),
    "users":   ("5372926953978341366", "👥"),
    "eyes":    ("5424885441100782420", "👀"),
    "eye":     ("5424892643760937442", "👁"),
    "brain":   ("5237799019329105246", "🧠"),
    "pc":      ("5424753383741346604", "🖥"),
    "snake":   ("5289608677244811430", "🐍"),
    "bolt":    ("5388849303982716989", "⚡️"),
    "skull":   ("5346088953181123923", "💀"),
    "dino":    ("5399987588700323376", "🦖"),
    "tracks":  ("5188501157072347830", "👣"),
    "speak":   ("5370765563226236970", "🗣"),
    "money":   ("5334754169414766749", "💵"),
    "alien":   ("5370869711888194012", "👾"),
    "love":    ("5402269792587495767", "😍"),
    "hug":     ("5370867268051806190", "🫂"),
    "coder":   ("5190458330719461749", "🧑‍💻"),
    "star_pe": ("5773970813732526413", "⭐"),
    "cloak":   ("5424846803575016194", "🌟"),
    "finger":  ("5417867232610894098", "👆"),
    "lock":    ("5258177567288401002", "🔒"),
    "bell":    ("5258174537842094855", "🔔"),
    "gear":    ("5258152182150077732", "⚙️"),
    "chain":   ("5296678515536581003", "🏷"),
    "mute_ic": ("5258267368877989660", "🔇"),
    "doc":     ("5258477770735885832", "📄"),
}


def pe(key: str) -> str:
    item = PE_TABLE.get(key)
    if not item:
        return key
    emoji_id, fallback = item
    if state.premium_emoji_active:
        return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>'
    return fallback


def by_line() -> str:
    return ''


def toggle_pe(active: bool) -> str:
    if active:
        return '<tg-emoji emoji-id="5848123819234955031">🗣</tg-emoji>'
    return '<tg-emoji emoji-id="5850449436651556295">🗣</tg-emoji>'


def status_pe(active: bool) -> str:
    return toggle_pe(active)
