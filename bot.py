import gc
import os
import subprocess
import imageio_ffmpeg
import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

TOKEN = os.getenv("BOT_TOKEN")
FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()

bot = telebot.TeleBot(TOKEN, threaded=False)

os.makedirs("temp", exist_ok=True)
user_fps = {}
ALLOWED_FPS = [15, 24, 30]

def get_keyboard(current_fps: int):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    buttons = [
        KeyboardButton(f"✅ {fps} FPS" if fps == current_fps else f"{fps} FPS")
        for fps in ALLOWED_FPS
    ]
    kb.row(*buttons)
    return kb

@bot.message_handler(commands=["start"])
def cmd_start(message):
    fps = user_fps.get(message.from_user.id, 30)
    bot.send_message(
        message.chat.id,
        f"🎬 Конвертер в WebM (VP9, 16:9, 512×288, без звука, <256 КБ).\n"
        f"Текущий FPS: {fps}\n\n"
        f"Отправь видео, GIF или фото (обрежь длину и кадр в Telegram перед отправкой).",
        reply_markup=get_keyboard(fps)
    )

@bot.message_handler(func=lambda m: m.text and m.text.endswith("FPS"))
def set_fps(message):
    try:
        fps_val = int(message.text.replace("✅", "").replace("FPS", "").strip())
        if fps_val in ALLOWED_FPS:
            user_fps[message.from_user.id] = fps_val
            bot.send_message(
                message.chat.id,
                f"⚙️ Выбрано: {fps_val} FPS",
                reply_markup=get_keyboard(fps_val)
            )
    except ValueError:
        pass

def convert_to_webm(input_path: str, output_path: str, fps: int, is_image: bool = False):
    vf = f"crop=iw:iw*9/16:(iw-ow)/2:(ih-oh)/2,scale=512:288:flags=neighbor,fps={fps}"
    
    cmd = [
        FFMPEG_PATH, "-y",
        "-probesize", "32k",
        "-analyzeduration", "0",
        "-threads", "1"
    ]
    if is_image:
        cmd += ["-loop", "1", "-t", "1", "-i", input_path]
    else:
        cmd += ["-t", "2.9", "-i", input_path]
        
    cmd += [
        "-an", "-sn", "-dn",
        "-vf", vf,
        "-c:v", "libvpx-vp9",
        "-deadline", "realtime",
        "-cpu-used", "8",
        "-lag-in-frames", "0",
        "-auto-alt-ref", "0",
        "-row-mt", "0",
        "-tile-columns", "0",
        "-frame-parallel", "0",
        "-threads", "1",
        "-b:v", "360k",
        "-maxrate", "400k",
        "-bufsize", "400k",
        "-pix_fmt", "yuv420p",
        output_path
    ]
    subprocess.run(cmd, check=True)

@bot.message_handler(content_types=["video", "animation", "video_note", "photo", "document"])
def handle_media(message):
    fps = user_fps.get(message.from_user.id, 30)
    is_image = False
    file_size = 0

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

    if file_size > 8 * 1024 * 1024:
        bot.reply_to(message, "⚠️ Файл больше 8 МБ. Обрежь его ножницами в Telegram перед отправкой.")
        return

    msg = bot.reply_to(message, f"⏳ Сжимаю ({fps} FPS)...")
    in_path = f"temp/{file_id}_in"
    out_path = f"temp/{file_id}.webm"

    try:
        file_info = bot.get_file(file_id)
        downloaded = bot.download_file(file_info.file_path)
        with open(in_path, "wb") as f:
            f.write(downloaded)
        del downloaded
        gc.collect()

        convert_to_webm(in_path, out_path, fps, is_image)

        size_kb = os.path.getsize(out_path) / 1024
        with open(out_path, "rb") as f:
            bot.send_document(
                message.chat.id,
                f,
                visible_file_name="sticker_16x9.webm",
                caption=f"✅ 512×288 | {fps} FPS | {size_kb:.1f} КБ"
            )
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка: {e}")
    finally:
        try:
            bot.delete_message(message.chat.id, msg.message_id)
        except Exception:
            pass
        if os.path.exists(in_path): os.remove(in_path)
        if os.path.exists(out_path): os.remove(out_path)
        gc.collect()

if __name__ == "__main__":
    print("Микро-бот запущен!")
    bot.infinity_polling(skip_pending=True)
