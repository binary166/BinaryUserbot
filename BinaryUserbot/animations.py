import asyncio
import state

CAT_FRAMES = [
    "=＾● ⋏ ●＾=",
    "=＾● ⋏ ●＾=\n\n  /|_/|\n ( o.o)\n  > ^ <",
    "=＾● ⋏ ●＾=\n\n    /\\_/\\\n   ( o.o )\n   / >🐟 \\",
    "=＾● ⋏ ●＾=\n\n    /\\_/\\\n   ( ^.^ )  ₊˚\n   (_)-(_)  ✧",
    "🌙  =＾● ⋏ ●＾=\n\n    /\\_/\\\n   ( -.- )  zzz\n   (  υ  )\n    ‾‾‾‾‾",
    "=＾● ⋏ ●＾=  🏃\n\n >ฅ^•ﻌ•^ฅ\n  ~  ~  ~",
    "=＾● ⋏ ●＾=  💨\n\n  ฅ^•ﻌ•^ฅ>\n    ~ ~ ~",
    "=＾● ⋏ ●＾=  🎵\n\n   ∧,,,∧\n  ( ̳• · • ̳)\n  /    づ♪",
    "=＾● ⋏ ●＾=  😸\n\n   ∧＿∧\n  (=^･ω･^=)\n    づ🌸",
    "✨ =＾● ⋏ ●＾= ✨\n\n  ╔═══════════╗\n  ║  ฅ^•ﻌ•^ฅ  ║\n  ║  Мяу! 🐾  ║\n  ╚═══════════╝",
]

async def run_animation(msg, frames: list, delay: float = 1.0, parse_mode: str = None):
    state.animating_msgs.add(msg.id)
    try:
        for i, frame in enumerate(frames):
            kwargs = {}
            if parse_mode:
                kwargs["parse_mode"] = parse_mode
            await msg.edit(frame, **kwargs)
            if i < len(frames) - 1:
                await asyncio.sleep(delay)
    except Exception as e:
        print(f"[ANIM] error: {e}")
    finally:
        await asyncio.sleep(5)
        state.animating_msgs.discard(msg.id)
