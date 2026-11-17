import asyncio
import os
import subprocess
import imageio_ffmpeg
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, FSInputFile, ReplyKeyboardMarkup, KeyboardButton

TOKEN = os.getenv("BOT_TOKEN")
FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()

bot = Bot(token=TOKEN)
dp = Dispatcher()

os.makedirs("temp", exist_ok=True)
user_fps = {}
ALLOWED_FPS = [15, 24, 30, 60]

def get_fps_keyboard(current_fps: int) -> ReplyKeyboardMarkup:
    row = []
    for fps in ALLOWED_FPS:
        label = f"✅ {fps} FPS" if fps == current_fps else f"{fps} FPS"
        row.append(KeyboardButton(text=label))
    return ReplyKeyboardMarkup(keyboard=[row], resize_keyboard=True)

@dp.message(CommandStart())
async def cmd_start(message: Message):
    fps = user_fps.get(message.from_user.id, 30)
    await message.answer(
        f"👋 Привет! Я конвертирую любые видео, GIF и фото в **WebM (VP9, 16:9, 512×288, без звука)**.\n\n"
        f"🎬 Текущая частота кадров: **{fps} FPS**\n"
        f"Выбери нужный FPS кнопками ниже и отправь мне файл (обрезать длину и кадр можно прямо в Telegram перед отправкой).",
        reply_markup=get_fps_keyboard(fps),
        parse_mode="Markdown"
    )

@dp.message(F.text.endswith("FPS"))
async def set_fps(message: Message):
    try:
        fps_val = int(message.text.replace("✅", "").replace("FPS", "").strip())
        if fps_val in ALLOWED_FPS:
            user_fps[message.from_user.id] = fps_val
            await message.answer(
                f"⚙️ Установлено: **{fps_val} FPS**",
                reply_markup=get_fps_keyboard(fps_val),
                parse_mode="Markdown"
            )
    except ValueError:
        pass

def convert_to_webm(input_path: str, output_path: str, fps: int, is_image: bool = False):
    vf_filter = f"crop=iw:iw*9/16:(iw-ow)/2:(ih-oh)/2,scale=512:288,fps={fps}"
    
    cmd = [FFMPEG_PATH, "-y"]
    if is_image:
        cmd += ["-loop", "1", "-t", "1", "-i", input_path]
    else:
        cmd += ["-t", "2.9", "-i", input_path]
        
    cmd += [
        "-vf", vf_filter,
        "-c:v", "libvpx-vp9",
        "-b:v", "450k",
        "-maxrate", "500k",
        "-bufsize", "500k",
        "-pix_fmt", "yuva420p",
        "-an",
        output_path
    ]
    subprocess.run(cmd, check=True)

@dp.message(F.video | F.animation | F.video_note | F.photo | F.document)
async def handle_media(message: Message):
    fps = user_fps.get(message.from_user.id, 30)
    msg = await message.answer(f"⏳ Конвертирую в WebM (VP9 16:9, {fps} FPS)...")
    
    is_image = False
    if message.video:
        file_id = message.video.file_id
    elif message.animation:
        file_id = message.animation.file_id
    elif message.video_note:
        file_id = message.video_note.file_id
    elif message.photo:
        file_id = message.photo[-1].file_id
        is_image = True
    elif message.document:
        file_id = message.document.file_id
        if message.document.mime_type and message.document.mime_type.startswith("image/"):
            is_image = True
    else:
        return

    file = await bot.get_file(file_id)
    in_path = f"temp/{file_id}_in"
    out_path = f"temp/{file_id}.webm"
    
    await bot.download_file(file.file_path, in_path)
    
    try:
        await asyncio.to_thread(convert_to_webm, in_path, out_path, fps, is_image)
        
        size_kb = os.path.getsize(out_path) / 1024
        doc = FSInputFile(out_path, filename="sticker_16x9.webm")
        await message.answer_document(
            doc, 
            caption=f"✅ Готово!\n📐 512×288 (16:9) | 🎞 {fps} FPS | 📦 {size_kb:.1f} КБ"
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")
    finally:
        await msg.delete()
        if os.path.exists(in_path): os.remove(in_path)
        if os.path.exists(out_path): os.remove(out_path)

async def main():
    print("Бот успешно запущен на Bot-Hosting.net!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
import asyncio
import os
import subprocess
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, FSInputFile, ReplyKeyboardMarkup, KeyboardButton

TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()

os.makedirs("temp", exist_ok=True)
user_fps = {}

def get_fps_keyboard(current_fps: int) -> ReplyKeyboardMarkup:
    row = []
    for fps in:
        label = f"✅ {fps} FPS" if fps == current_fps else f"{fps} FPS"
        row.append(KeyboardButton(text=label))
    return ReplyKeyboardMarkup(keyboard=[row], resize_keyboard=True)

@dp.message(CommandStart())
async def cmd_start(message: Message):
    fps = user_fps.get(message.from_user.id, 30)
    await message.answer(
        f"👋 Привет! Я конвертирую любые видео, GIF и фото в **WebM (VP9, 16:9, 512×288, без звука)**.\n\n"
        f"🎬 Текущая частота кадров: **{fps} FPS**\n"
        f"Выбери нужный FPS кнопками ниже и отправь мне файл (обрезать длину и кадр можно прямо в Telegram перед отправкой).",
        reply_markup=get_fps_keyboard(fps),
        parse_mode="Markdown"
    )

@dp.message(F.text.endswith("FPS"))
async def set_fps(message: Message):
    try:
        fps_val = int(message.text.replace("✅", "").replace("FPS", "").strip())
        if fps_val in:
            user_fps[message.from_user.id] = fps_val
            await message.answer(
                f"⚙️ Установлено: **{fps_val} FPS**",
                reply_markup=get_fps_keyboard(fps_val),
                parse_mode="Markdown"
            )
    except ValueError:
        pass

def convert_to_webm(input_path: str, output_path: str, fps: int, is_image: bool = False):
    vf_filter = f"crop=iw:iw*9/16:(iw-ow)/2:(ih-oh)/2,scale=512:288,fps={fps}"
    
    cmd = ["ffmpeg", "-y"]
    if is_image:
        cmd += ["-loop", "1", "-t", "1", "-i", input_path]
    else:
        cmd += ["-t", "2.9", "-i", input_path]
        
    cmd += [
        "-vf", vf_filter,
        "-c:v", "libvpx-vp9",
        "-b:v", "450k",
        "-maxrate", "500k",
        "-bufsize", "500k",
        "-pix_fmt", "yuva420p",
        "-an",
        output_path
    ]
    subprocess.run(cmd, check=True)

@dp.message(F.video | F.animation | F.video_note | F.photo | F.document)
async def handle_media(message: Message):
    fps = user_fps.get(message.from_user.id, 30)
    msg = await message.answer(f"⏳ Конвертирую в WebM (VP9 16:9, {fps} FPS)...")
    
    is_image = False
    if message.video:
        file_id = message.video.file_id
    elif message.animation:
        file_id = message.animation.file_id
    elif message.video_note:
        file_id = message.video_note.file_id
    elif message.photo:
        file_id = message.photo[-1].file_id
        is_image = True
    elif message.document:
        file_id = message.document.file_id
        if message.document.mime_type and message.document.mime_type.startswith("image/"):
            is_image = True
    else:
        return

    file = await bot.get_file(file_id)
    in_path = f"temp/{file_id}_in"
    out_path = f"temp/{file_id}.webm"
    
    await bot.download_file(file.file_path, in_path)
    
    try:
        await asyncio.to_thread(convert_to_webm, in_path, out_path, fps, is_image)
        
        size_kb = os.path.getsize(out_path) / 1024
        doc = FSInputFile(out_path, filename="sticker_16x9.webm")
        await message.answer_document(
            doc, 
            caption=f"✅ Готово!\n📐 512×288 (16:9) | 🎞 {fps} FPS | 📦 {size_kb:.1f} КБ"
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")
    finally:
        await msg.delete()
        if os.path.exists(in_path): os.remove(in_path)
        if os.path.exists(out_path): os.remove(out_path)

async def health_check(request):
    return web.Response(text="Bot is alive!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

async def main():
    await start_web_server()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
