import os
from dotenv import load_dotenv
import telebot
from telebot import types
from telebot.types import ReactionTypeEmoji
import os
import speech_recognition as sr
from pydub import AudioSegment

# 1. Load env
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

# 2. /start command FIRST
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message: types.Message):
    bot.reply_to(message, "im alive. use /sendvoice to test the audio sending feature.")

# 3. Voice/audio handler

@bot.message_handler(content_types=['voice', 'audio'])
def handle_audio(message: types.Message):
    chat_id = message.chat.id
    
    try:
        # 1. Download file from Telegram
        if message.voice:
            file_id = message.voice.file_id
        else:
            file_id = message.audio.file_id
        
        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        # 2. Save as .ogg
        ogg_path = f"temp_{file_id}.ogg"
        with open(ogg_path, 'wb') as f:
            f.write(downloaded_file)
        
        # 3. Convert from OGG to WAV 
        wav_path = f"temp_{file_id}.wav"
        audio = AudioSegment.from_file(ogg_path, format="ogg")
        audio.export(wav_path, format="wav")
        
        # 4. Transcribe 
        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_path) as source:
            audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data, language='en-SG') 
        
        # 5. Reply with transcription
        bot.reply_to(message, f"**Transcription**:\n`{text}`")
        
    except sr.UnknownValueError:
        bot.reply_to(message, "❌ Could not understand the audio.")
    
    finally:
        # 6. Clean up temp files
        for path in [locals().get('ogg_path'), locals().get('wav_path')]:
            if path and os.path.exists(path):
                os.remove(path)

# 4. /sendvoice command
@bot.message_handler(commands=['sendvoice'])
def send_voice_in_group(message):
    chat_id = message.chat.id
    voice_path = "hello-46355.mp3"  

    with open(voice_path, 'rb') as f:
        bot.send_voice(chat_id, f)


# 6. Reaction handler
@bot.message_handler(func=lambda m: True, content_types=['text', 'photo', 'document', 'video'])
def react_to_messages(message: types.Message):
    chat_id = message.chat.id
    
    try:
        bot.set_message_reaction(chat_id, message.id, [ReactionTypeEmoji('👍')], is_big=False)
    except Exception as e:
        print("Reaction error:", e)

if __name__ == "__main__":
    print("Bot running in group...")
    bot.infinity_polling()
