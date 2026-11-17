import asyncio
import gc
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

# Только разрешенные Telegram значения FPS для видеостикеров
ALLOWED_FPS = [15, 24, 30]

def get_fps_keyboard(current_fps: int) -> ReplyKeyboardMarkup:
    row = [
        KeyboardButton(text=f"✅ {fps} FPS" if fps == current_fps else f"{fps} FPS")
        for fps in ALLOWED_FPS
    ]
    return ReplyKeyboardMarkup(keyboard=[row], resize_keyboard=True)

@dp.message(CommandStart())
async def cmd_start(message: Message):
    fps = user_fps.get(message.from_user.id, 30)
    await message.answer(
        f"🎬 Конвертер в **WebM (VP9, 16:9, 512×288, без звука, <256 КБ)**.\n"
        f"Текущий FPS: **{fps}**\n\n"
        f"Отправь видео, GIF или фото (обрезать длину и кадр можно прямо в Telegram перед отправкой).",
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
                f"⚙️ Выбрано: **{fps_val} FPS**",
                reply_markup=get_fps_keyboard(fps_val),
                parse_mode="Markdown"
            )
    except ValueError:
        pass

def convert_to_webm(input_path: str, output_path: str, fps: int, is_image: bool = False):
    # Кроп по центру в 16:9 + быстрое сжатие до 512x288 без лишней нагрузки на ОЗУ
    vf_filter = f"crop=iw:iw*9/16:(iw-ow)/2:(ih-oh)/2,scale=512:288:flags=fast_bilinear,fps={fps}"
    
    cmd = [FFMPEG_PATH, "-y", "-threads", "1"]
    if is_image:
        cmd += ["-loop", "1", "-t", "1", "-i", input_path]
    else:
        cmd += ["-t", "2.9", "-i", input_path]
        
    cmd += [
        "-vf", vf_filter,
        "-c:v", "libvpx-vp9",
        "-deadline", "realtime",
        "-cpu-used", "8",
        "-lag-in-frames", "0",
        "-auto-alt-ref", "0",
        "-threads", "1",
        "-b:v", "380k",
        "-maxrate", "420k",
        "-bufsize", "420k",
        "-pix_fmt", "yuv420p",
        "-an",
        output_path
    ]
    subprocess.run(cmd, check=True)

@dp.message(F.video | F.animation | F.video_note | F.photo | F.document)
async def handle_media(message: Message):
    fps = user_fps.get(message.from_user.id, 30)
    
    file_size = 0
    is_image = False
    if message.video:
        file_id = message.video.file_id
        file_size = message.video.file_size or 0
    elif message.animation:
        file_id = message.animation.file_id
        file_size = message.animation.file_size or 0
    elif message.video_note:
        file_id = message.video_note.file_id
        file_size = message.video_note.file_size or 0
    elif message.photo:
        file_id = message.photo[-1].file_id
        file_size = message.photo[-1].file_size or 0
        is_image = True
    elif message.document:
        file_id = message.document.file_id
        file_size = message.document.file_size or 0
        if message.document.mime_type and message.document.mime_type.startswith("image/"):
            is_image = True
    else:
        return

    # Ограничение в 10 МБ для защиты контейнера на 256 МБ ОЗУ
    if file_size > 10 * 1024 * 1024:
        await message.answer("⚠️ Файл больше 10 МБ. Обрежьте его ножницами в Telegram перед отправкой.")
        return

    msg = await message.answer(f"⏳ Сжимаю в WebM ({fps} FPS)...")
    
    file = await bot.get_file(file_id)
    in_path = f"temp/{file_id}_in"
    out_path = f"temp/{file_id}.webm"
    
    await bot.download_file(file.file_path, in_path)
    gc.collect()
    
    try:
        await asyncio.to_thread(convert_to_webm, in_path, out_path, fps, is_image)
        
        size_kb = os.path.getsize(out_path) / 1024
        doc = FSInputFile(out_path, filename="sticker_16x9.webm")
        await message.answer_document(
            doc, 
            caption=f"✅ 512×288 | {fps} FPS | {size_kb:.1f} КБ"
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")
    finally:
        await msg.delete()
        if os.path.exists(in_path): os.remove(in_path)
        if os.path.exists(out_path): os.remove(out_path)
        gc.collect()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
