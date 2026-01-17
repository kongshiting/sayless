from dotenv import load_dotenv
import telebot
from telebot import types
from telebot.types import ReactionTypeEmoji
import os
import speech_recognition as sr
from pydub import AudioSegment

# Import your engine
from emotion_engine import EmotionEngine

# 1. Load env
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

# Initialize the Engine
engine = EmotionEngine()

# 2. /start command
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message: types.Message):
    # Only use text for instructions
    bot.reply_to(message, "SayLess is ready. Send me a voice message, and I'll react based on your tone.")

# 3. Voice/audio handler - The Core Logic
@bot.message_handler(content_types=['voice', 'audio'])
def handle_audio(message: types.Message):
    chat_id = message.chat.id
    
    try:
        # 1. Download file from Telegram
        file_id = message.voice.file_id if message.voice else message.audio.file_id
        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        # 2. Save and Convert (Standard Pipeline)
        ogg_path = f"temp_{file_id}.ogg"
        wav_path = f"temp_{file_id}.wav"
        
        with open(ogg_path, 'wb') as f:
            f.write(downloaded_file)
        
        audio = AudioSegment.from_file(ogg_path, format="ogg")
        audio.export(wav_path, format="wav")
        
        # 3. Transcribe 
        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_path) as source:
            audio_data = recognizer.record(source)
            # Transcribe but DON'T reply with it
            text = recognizer.recognize_google(audio_data, language='en-SG') 
        
        # 4. Detect Emotion from the hidden transcription
        detected_emoji = engine.detect_emotion(text)
        
        # 5. Set Reaction ONLY (No text bubble reply)
        # This reacts directly to the voice note you just sent
        bot.set_message_reaction(chat_id, message.id, [ReactionTypeEmoji(detected_emoji)], is_big=False)
        
    except sr.UnknownValueError:
        # Optional: React with a 'thinking' or 'confused' emoji if audio is unclear
        bot.set_message_reaction(chat_id, message.id, [ReactionTypeEmoji("🤔")])
    except Exception as e:
        print(f"Error processing audio: {e}")
    
    finally:
        # 6. Clean up temp files
        for path in [locals().get('ogg_path'), locals().get('wav_path')]:
            if path and os.path.exists(path):
                os.remove(path)

if __name__ == "__main__":
    print("SayLess Bot is running (Audio Reaction Mode)...")
    bot.infinity_polling()