import os
import random
import requests
from pydub import AudioSegment
from pydub.effects import normalize
from dotenv import load_dotenv
import time
from keyword_phrases import extract_key_phrases

load_dotenv()

FREESOUND_API_KEY = os.getenv("FREESOUND_API_KEY")
BASE_URL = "https://freesound.org/apiv2/search/text/"

# Enhanced keyword mapping - maps extracted keywords to better search terms
KEYWORD_MAPPING = {
    # Time phrases
    "today": "clock ticking",
    "yesterday": "calendar flip",
    "tomorrow": "alarm clock",
    "after lunch": "eating utensils",
    "before lunch": "stomach growl",
    "next day": "rooster crow",
    
    # Weather
    "raining": "rain heavy",
    "weather": "wind rain",
    
    # Emotions
    "insecure": "nervous breathing",
    "anxious": "heartbeat fast",
    "stressed": "deep sigh",
    "worried": "nervous breath",
    "scared": "gasp fear",
    "sad": "crying sad",
    "angry": "angry yell",
    "upset": "sigh heavy",
    "happy": "laugh happy",
    "excited": "cheer excited",
    "tired": "yawn tired",
    "tiring": "exhausted sigh",
    "hungry": "stomach growl",
    "confused": "huh confused",
    "awkward": "awkward silence",
    "devastated": "crying sobbing",
    "embarrassed": "nervous laugh",
    
    # Common actions/verbs
    "wake": "alarm clock beeping",
    "woke": "alarm clock",
    "sleep": "snoring sleep",
    "overslept": "alarm loud",
    "miss": "whoosh miss",
    "missed": "ding miss",
    "rush": "running footsteps fast",
    "rushed": "running fast",
    "run": "running footsteps",
    "ran": "running",
    "running": "running footsteps",
    "drop": "object drop",
    "dropped": "drop floor",
    "spill": "liquid spill",
    "spilled": "water splash",
    "cry": "crying sobbing",
    "cried": "crying",
    "laugh": "laughing",
    "laughed": "laughter",
    "shower": "shower running",
    "showered": "shower water",
    "forget": "woosh forget",
    "forgot": "doh mistake",
    "call": "phone ringing",
    "called": "phone ring",
    "reach": "door open",
    "reached": "arrive",
    "realise": "aha realization",
    "realised": "light bulb",
    "realize": "aha moment",
    "realized": "gasp realization",
    "wear": "clothes rustle",
    "wearing": "fabric rustle",
    "wore": "zipper",
    "choose": "click decision",
    "choosing": "hmm thinking",
    "chose": "ding choice",
    "argue": "argument angry",
    "argued": "yelling argument",
    "disagree": "no disagreement",
    "disagreement": "argument",
    "break": "glass breaking",
    "broke": "break crash",
    "broken": "shatter break",
    "cheat": "sneak cheating",
    "cheated": "gasp shock",
    "scream": "scream loud",
    "screaming": "scream",
    "rain": "rain",
    "rained": "rain storm",
    "want": "desire hmm",
    "wanted": "wish",
    "go": "footsteps walking",
    "home": "door close",
    "go home": "door unlock",
    
    # Generic fallbacks
    "neutral": "ambient room tone",
    "tiring day": "exhausted sigh",
    "whole day": "clock ticking",
}

MIN_DURATION = 0.3
MAX_DURATION = 5.0
TARGET_CLIP_LENGTH_MS = 2000
SILENCE_MS = 120

# ==================
# CUSTOM SOUND POOLS
# ==================
# Format: "pool_name": ["path/to/sound1.mp3", "path/to/sound2.mp3", ...]
# The script will randomly pick one sound from the pool

SOUND_POOLS = {
    # Swear words pool - all swear words share these sounds
    "swear_words": [
        "custom_sounds/censor.mp3",
        "custom_sounds/Wah cb.mp3",
        "custom_sounds/Wah cb_2.mp3",
        "custom_sounds/Prostitute.mp3"
    ],
    
    # Surprise/shock pool
    "surprise": [
        "custom_sounds/OMG.mp3"
    ],
    
    # Dog sound pool
    "dog": [
        "custom_sounds/Bark.mp3",
        "custom_sounds/Dog growl.mp3",
        "custom_sounds/High Pitched Woof.mp3",
        "custom_sounds/Loud Woof.mp3",
        "custom_sounds/Many Woofs.mp3"
    ],

    "cat": [
        "custom_sounds/High Pitch Meow.mp3",
        "custom_sounds/Low Meow.mp3",
        "custom_sounds/Meow_2.mp3",
        "custom_sounds/meow.mp3"
    ],
}


# ============================================================
# KEYWORD TO POOL MAPPING - MAP WORDS TO POOLS
# ============================================================
# Format: "keyword": "pool_name"
# Multiple keywords can map to the same pool

KEYWORD_TO_POOL = {
    # Swear words - all map to "swear_words" pool
    "fuck": "swear_words",
    "fucking": "swear_words",
    "fucked": "swear_words",
    "shit": "swear_words",
    "damn": "swear_words",
    "ass": "swear_words",
    "bitch": "swear_words",
    "hell": "swear_words",
    "chibai": "swear_words",
    "cheebye": "swear_words",
    
    # Surprise - all map to "surprise" pool
    "shocked": "surprise",
    "surprised": "surprise",
    "unexpected": "surprise",
    "omg": "surprise",
    
    # Cat - all map to "cat" pool
    "cat": "cat",
    "meow": "cat",
    "meowed": "cat",
    "cats": "cat",
    "feline": "cat",
    "meowing": "cat",
    "kitten": "cat",
    "kitty": "cat",

    # Dog - all map to "dog" pool
    "dog": "dog",
    "woof": "dog",
    "dogs": "dog",
    "doggo": "dog",
    "doge": "dog",
    "woofed": "dog",
    "woofing": "dog",
    "bark": "dog",
    "barking": "dog",
    "barked": "dog",
    "puppy": "dog",
}


def normalize_keyword(keyword):
    """Convert extracted keyword to optimized search term"""
    keyword_lower = keyword.lower().strip()
    
    # Direct mapping
    if keyword_lower in KEYWORD_MAPPING:
        return KEYWORD_MAPPING[keyword_lower]
    
    # Multi-word phrases - try to find the main keyword
    words = keyword_lower.split()
    for word in words:
        if word in KEYWORD_MAPPING:
            return KEYWORD_MAPPING[word]
    
    # No mapping found - use as is
    return keyword_lower


def search_freesound(keyword):
    """Search Freesound for sound effects"""
    if not FREESOUND_API_KEY:
        print("[ERROR] FREESOUND_API_KEY not found in .env file")
        print("Get free API key at: https://freesound.org/apiv2/apply/")
        return []
    
    search_term = normalize_keyword(keyword)
    
    params = {
        "query": search_term,
        "filter": f"duration:[{MIN_DURATION} TO {MAX_DURATION}]",
        "sort": "downloads_desc",
        "fields": "id,name,previews,duration,download,num_downloads,avg_rating,tags",
        "page_size": 30
    }
    
    headers = {
        "Authorization": f"Token {FREESOUND_API_KEY}"
    }
    
    try:
        print(f"[DEBUG] Searching for '{keyword}' → '{search_term}'")
        response = requests.get(BASE_URL, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        sounds = data.get("results", [])
        
        if sounds:
            print(f"[INFO] Found {len(sounds)} sounds")
        else:
            print(f"[WARN] No sounds found")
        
        return sounds
        
    except Exception as e:
        print(f"[ERROR] Search failed: {e}")
        return []


def score_sound(sound, keyword):
    """Score a sound based on relevance and quality"""
    score = 0
    
    # Downloads (0-40 points)
    downloads = sound.get("num_downloads", 0)
    score += min(downloads / 100, 40)
    
    # Rating (0-25 points)
    rating = sound.get("avg_rating", 0)
    score += rating * 5
    
    # Duration preference (0-25 points)
    duration = sound.get("duration", 10)
    if duration <= 1.5:
        score += 25
    elif duration <= 2.5:
        score += 18
    elif duration <= 4:
        score += 10
    else:
        score += 5
    
    # Keyword matching (0-10 points)
    name = sound.get("name", "").lower()
    tags = " ".join(sound.get("tags", [])).lower()
    keyword_lower = keyword.lower()
    
    if keyword_lower in name:
        score += 10
    elif keyword_lower in tags:
        score += 5
    
    return score


def download_sound(sound):
    """Download sound from Freesound"""
    try:
        audio_url = sound["previews"]["preview-hq-mp3"]
        
        print(f"[INFO] Downloading: {sound['name'][:50]}...")
        
        response = requests.get(audio_url, timeout=30, stream=True)
        response.raise_for_status()
        
        filename = f"tmp_freesound_{sound['id']}.mp3"
        
        with open(filename, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        return filename
        
    except Exception as e:
        print(f"[ERROR] Download failed: {e}")
        return None


def process_sound(filepath):
    """Process audio file"""
    try:
        audio = AudioSegment.from_file(filepath)

        # Trim to target length
        if len(audio) > TARGET_CLIP_LENGTH_MS:
            audio = audio[:TARGET_CLIP_LENGTH_MS]

        # Normalize volume
        audio = normalize(audio)

        return audio
        
    except Exception as e:
        print(f"[ERROR] Failed to process {filepath}: {e}")
        return None


def load_custom_sound(keyword):
    """Load a custom sound file from a pool for specific keywords"""
    keyword_lower = keyword.lower().strip()
    
    # Check if this keyword maps to a sound pool
    if keyword_lower not in KEYWORD_TO_POOL:
        return None
    
    pool_name = KEYWORD_TO_POOL[keyword_lower]
    
    # Check if the pool exists
    if pool_name not in SOUND_POOLS:
        print(f"[WARN] Pool '{pool_name}' not found for keyword '{keyword}'")
        return None
    
    sound_files = SOUND_POOLS[pool_name]
    
    # Filter to only files that exist
    available_files = [f for f in sound_files if os.path.exists(f)]
    
    if not available_files:
        print(f"[WARN] No custom sound files found in pool '{pool_name}' for '{keyword}'")
        print(f"[WARN] Looking for files:")
        for f in sound_files:
            print(f"  - {f} (exists: {os.path.exists(f)})")
        return None
    
    # Randomly pick one from the pool
    chosen_file = random.choice(available_files)
    print(f"[INFO] Using custom sound from '{pool_name}' pool: {os.path.basename(chosen_file)}")
    
    try:
        audio = AudioSegment.from_file(chosen_file)
        
        # Trim to target length
        if len(audio) > TARGET_CLIP_LENGTH_MS:
            audio = audio[:TARGET_CLIP_LENGTH_MS]
        
        # Normalize volume
        audio = normalize(audio)
        
        return audio
        
    except Exception as e:
        print(f"[ERROR] Failed to load custom sound {chosen_file}: {e}")
        return None


def keyword_to_audio(keyword):
    """Convert keyword to audio clip - checks custom sound pools first"""
    keyword_lower = keyword.lower().strip()
    
    # Check if this keyword maps to a custom sound pool
    if keyword_lower in KEYWORD_TO_POOL:
        custom_audio = load_custom_sound(keyword_lower)
        if custom_audio:
            return custom_audio
        # If custom sound failed, fall through to regular search
        print(f"[INFO] Custom sound failed, falling back to Freesound search for '{keyword}'")
    
    # Regular Freesound search
    sounds = search_freesound(keyword)
    
    if not sounds:
        print(f"[SKIP] No sounds for '{keyword}'")
        return None
    
    # Score and sort sounds
    scored_sounds = [(score_sound(s, keyword), s) for s in sounds]
    scored_sounds.sort(reverse=True, key=lambda x: x[0])
    
    # Try top 5 sounds
    for score, sound in scored_sounds[:5]:
        filepath = download_sound(sound)
        if not filepath:
            continue
        
        audio = process_sound(filepath)
        
        # Cleanup
        if os.path.exists(filepath):
            os.remove(filepath)
        
        if audio:
            time.sleep(0.3)
            return audio
    
    return None


def transcript_to_soundbite(transcript: str, output_file: str = "soundbite.ogg", max_keywords: int = 8):
    """
    Convert a transcript into a soundbite audio file
    
    Args:
        transcript: The text transcript to analyze
        output_file: Output filename for the soundbite
        max_keywords: Maximum number of keywords/sounds to include
    
    Returns:
        Path to the generated soundbite file, or None if failed
    """
    if not FREESOUND_API_KEY:
        print("=" * 60)
        print("ERROR: FREESOUND_API_KEY not found")
        print("=" * 60)
        print("Add to your .env file:")
        print("FREESOUND_API_KEY=your_api_key_here")
        print("=" * 60)
        return None
    
    # Extract regular keywords from transcript
    print("\n" + "=" * 60)
    print("EXTRACTING KEYWORDS FROM TRANSCRIPT")
    print("=" * 60)
    keywords = extract_key_phrases(transcript, max_k=max_keywords)
    
    print(f"[INFO] Raw extracted keywords: {keywords}")
    
    # Process keywords to handle custom sounds
    processed_keywords = []
    custom_words_found = []
    
    for keyword in keywords:
        # Check if this keyword contains any custom-mapped words
        keyword_lower = keyword.lower()
        keyword_words = keyword_lower.split()
        
        has_custom = False
        custom_in_phrase = []
        
        # Check each word in the keyword phrase
        for word in keyword_words:
            if word in KEYWORD_TO_POOL:
                has_custom = True
                custom_in_phrase.append(word)
        
        if has_custom:
            # Add only the custom words (not the full phrase)
            for custom_word in custom_in_phrase:
                if custom_word not in processed_keywords:
                    processed_keywords.append(custom_word)
                    custom_words_found.append(custom_word)
        else:
            # No custom words - add the full phrase
            processed_keywords.append(keyword)
    
    print(f"[INFO] Processed keywords: {processed_keywords}")
    if custom_words_found:
        custom_pools = {KEYWORD_TO_POOL.get(kw, "unknown") for kw in custom_words_found}
        print(f"[INFO] Detected custom keywords: {custom_words_found}")
        print(f"[INFO] Using sound pools: {custom_pools}")
    
    # Build soundbite
    print("\n" + "=" * 60)
    print("GENERATING SOUNDBITE")
    print("=" * 60)
    
    final_audio = AudioSegment.silent(duration=0)
    successful_clips = 0

    for keyword in processed_keywords:
        print(f"\n--- Processing: '{keyword}' ---")
        
        clip = keyword_to_audio(keyword)
        if clip:
            final_audio += clip
            final_audio += AudioSegment.silent(duration=SILENCE_MS)
            successful_clips += 1

    if len(final_audio) == 0:
        print("\n[ERROR] No audio clips were generated.")
        return None

    # Export
    final_audio.export(
        output_file,
        format="ogg",
        codec="libopus",
        parameters=["-ac", "1"]
    )

    print("\n" + "=" * 60)
    print(f"[OK] Soundbite created: {output_file}")
    print(f"[INFO] Duration: {len(final_audio)/1000:.2f}s")
    print(f"[INFO] Clips used: {successful_clips}/{len(processed_keywords)}")
    print("=" * 60)
    
    return output_file


if __name__ == "__main__":
    # Example usage with custom sound pools
    sample_transcript = """
    dog cat woof fuck omg bark cb chi bai meow bark
    """
    
    transcript_to_soundbite(sample_transcript, output_file="my_day.ogg", max_keywords=15)