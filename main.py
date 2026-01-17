from dotenv import load_dotenv
import telebot
from telebot import types
from telebot.types import ReactionTypeEmoji
import os
import speech_recognition as sr
from pydub import AudioSegment

# Import your engine
from emotion_engine import EmotionEngine
from soundbite_generator import transcript_to_soundbite

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

    ogg_path = None
    wav_path = None
    soundbite_path = None
    
    try:
        # 1. Download file from Telegram
        file_id = message.voice.file_id if message.voice else message.audio.file_id
        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        # 2. Save and Convert
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
            transcript = recognizer.recognize_google(audio_data, language='en-SG') 
        
        print(f"[TRANSCRIPT] {transcript}")
        
        # 4. Detect Emotion from the hidden transcription
        detected_emoji = engine.detect_emotion(transcript)
        print(f"[EMOTION] {detected_emoji}")
        
        # 5. Generate Soundbite from transcript
        soundbite_path = f"soundbite_{file_id}.ogg"
        result = transcript_to_soundbite(
            transcript, 
            output_file=soundbite_path, 
            max_keywords=8
        )
        if result and os.path.exists(soundbite_path):
            # 6. Send soundbite as voice message
            with open(soundbite_path, 'rb') as voice_file:
                sent_message = bot.send_voice(
                    chat_id,
                    voice_file,
                    reply_to_message_id=message.id
                )

            # 7. Set emoji reaction on the soundbite we just sent
            bot.set_message_reaction(
                chat_id, 
                sent_message.id, 
                [ReactionTypeEmoji(detected_emoji)], 
                is_big=False)
        
            print(f"[SUCCESS] Soundbite sent with {detected_emoji} reaction")

        else:
            # Fallback: just react to original message if soundbite generation failed
            bot.set_message_reaction(
                chat_id, 
                message.id, 
                [ReactionTypeEmoji(detected_emoji)]
            )
            bot.reply_to(message, "⚠️ Could not generate soundbite, but detected your emotion!")

    except sr.UnknownValueError:
        # Audio unclear - react with thinking emoji
        bot.set_message_reaction(chat_id, message.id, [ReactionTypeEmoji("🤔")])
        bot.reply_to(message, "🤔 Could not understand the audio")
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()

        # React with error emoji
        try:
            bot.set_message_reaction(chat_id, message.id, [ReactionTypeEmoji("❌")])
        except:
            pass
        bot.reply_to(message, f"❌ Error processing: {str(e)[:100]}")
    
    finally:
        # 8. Clean up temp files
        for path in [ogg_path, wav_path, soundbite_path]:
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                    print(f"[CLEANUP] Removed {path}")
                except Exception as e:
                    print(f"[CLEANUP ERROR] Could not remove {path}: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("SayLess Bot is running!")
    print("Features:")
    print("  ✅ Transcription")
    print("  ✅ Keyword extraction")
    print("  ✅ Soundbite generation")
    print("  ✅ Emoji reactions")
    print("=" * 60)
    bot.infinity_polling()