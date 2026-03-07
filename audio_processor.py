"""Module for processing voice/audio messages using OpenAI Whisper."""
from openai import OpenAI
from telegram import Update
from config import OPENAI_API_KEY


async def transcribe_audio(update: Update, context) -> str:
    """Download voice/audio from Telegram and transcribe with Whisper."""
    try:
        if update.message.voice:
            file_id = update.message.voice.file_id
            filename = "voice.ogg"
        elif update.message.audio:
            file_id = update.message.audio.file_id
            filename = update.message.audio.file_name or "audio.mp3"
        else:
            return ""

        file = await context.bot.get_file(file_id)
        audio_bytes = await file.download_as_bytearray()

        client = OpenAI(api_key=OPENAI_API_KEY)
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=(filename, bytes(audio_bytes)),
        )
        return transcript.text.strip()
    except Exception as e:
        print(f"Error transcribing audio: {e}")
        return ""
