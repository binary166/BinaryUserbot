"""
Анимации: кадры для cat, rocket, pokemon + универсальный runner.
"""
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

ROCKET_FRAMES = [
    "🌍\n\n\n\n\n\n\n🚀",
    "🌍\n\n\n\n\n\n🚀\n ",
    "🌍\n\n\n\n\n🚀\n\n ",
    "🌍\n\n\n\n🚀\n\n\n ",
    "🌍\n\n\n🚀\n\n\n\n ",
    "🌍\n\n🚀\n\n\n\n\n ",
    "🌍\n🚀 💨\n\n\n\n\n\n ",
    "🌌 ✨ 🌟\n  🚀\n   ⭐\n    ✨\n",
    "🌌 🌟 ✨ ⭐\n    🚀 💫\n",
    "🌌 🌟 ✨ ⭐ 💫\n          🚀\n              🌕",
    "🌕 ← 🚀✅\n\n🌌 🌟 ✨ ⭐ 💫\n\n🌍 — старт выполнен!",
    "🌕🚀\n\n⭐ <b>Мы на Луне!</b> ⭐\n\n🌌 🌟 ✨ 💫 🌍",
]

POKEMON_FRAMES = [
    "⚔️ <b>БИТВА НАЧАЛАСЬ!</b>\n\n🔥 vs 💧",
    "🔥 <b>Чармандер</b>   vs   <b>Сквиртл</b> 💧\n\n❤️❤️❤️❤️❤️   ❤️❤️❤️❤️❤️",
    "🔥 <b>Чармандер</b>   vs   <b>Сквиртл</b> 💧\n\n❤️❤️❤️❤️❤️   ❤️❤️❤️❤️❤️\n\n🔥 Использует <b>Огонь!</b>",
    "🔥 <b>Чармандер</b>   vs   <b>Сквиртл</b> 💧\n\n❤️❤️❤️❤️❤️   ❤️❤️❤️❤️\n\n💥 <i>Удар нанесён!</i> -1 ❤️",
    "🔥 <b>Чармандер</b>   vs   <b>Сквиртл</b> 💧\n\n❤️❤️❤️❤️   ❤️❤️❤️❤️\n\n💥 <i>Удар нанесён!</i> -1 ❤️",
    "🔥 <b>Чармандер</b>   vs   <b>Сквиртл</b> 💧\n\n❤️❤️❤️❤️   ❤️❤️\n\n💥💥 <i>Супер эффективно!</i> -2 ❤️",
    "🔥 <b>Чармандер</b>   vs   <b>Сквиртл</b> 💧\n\n❤️❤️❤️❤️   ❤️❤️\n\n🔥⚡ <b>МЕГА УДАР!!!</b>",
    "🔥 <b>Чармандер</b>   vs   <b>Сквиртл</b> 💧\n\n❤️❤️❤️❤️   💀\n\n💥💥💥 <i>Нокаут!</i>",
    "🏆 <b>Чармандер ПОБЕДИЛ!</b> 🔥\n\n🎉 +150 опыта\n⭐ Уровень повышен!\n\n🔥🔥🔥",
    "🎊 <b>ПОБЕДА!</b> 🎊\n\n🔥 <b>ЧАРМАНДЕР</b> 🔥\n\n❤️❤️  HP: 40/100\n✨ XP: ████████ MAX",
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
