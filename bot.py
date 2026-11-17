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
        f"👋 Привет! Я конвертирую видео, GIF и фото в **WebM (VP9, 16:9, 512×288, без звука)**.\n\n"
        f"🎬 Текущая частота кадров: **{fps} FPS**\n"
        f"Выбери FPS кнопками ниже и отправь файл (обрезать длину и кадр можно прямо в Telegram перед отправкой).",
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
    # Сразу уменьшаем кадр до 512x288 с кропом 16:9 на этапе декодирования, чтобы не держать в памяти HD-кадры
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
        "-cpu-used", "8",          # Максимальная скорость и минимальный расход ОЗУ
        "-lag-in-frames", "0",     # Отключаем буфер будущих кадров (экономит до 100 МБ ОЗУ)
        "-auto-alt-ref", "0",      # Отключаем альтернативные опорные кадры (экономит ОЗУ)
        "-threads", "1",
        "-b:v", "420k",
        "-maxrate", "480k",
        "-bufsize", "480k",
        "-pix_fmt", "yuv420p",     # Без альфа-канала для экономии 25% памяти
        "-an",
        output_path
    ]
    subprocess.run(cmd, check=True)

@dp.message(F.video | F.animation | F.video_note | F.photo | F.document)
async def handle_media(message: Message):
    fps = user_fps.get(message.from_user.id, 30)
    
    # Проверка размера входящего файла (не больше 15 МБ для 256 МБ ОЗУ)
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

    if file_size > 15 * 1024 * 1024:
        await message.answer("⚠️ Файл слишком тяжелый (>15 МБ). Обрежьте его в редакторе Telegram перед отправкой.")
        return

    msg = await message.answer(f"⏳ Конвертирую в WebM (16:9, {fps} FPS)...")
    
    file = await bot.get_file(file_id)
    in_path = f"temp/{file_id}_in"
    out_path = f"temp/{file_id}.webm"
    
    await bot.download_file(file.file_path, in_path)
    gc.collect() # Очищаем память перед запуском FFmpeg
    
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
        gc.collect()

async def main():
    print("Бот запущен в режиме экономии памяти!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
