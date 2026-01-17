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


def keyword_to_audio(keyword):
    """Convert keyword to audio clip"""
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
    
    # Extract keywords from transcript
    print("\n" + "=" * 60)
    print("EXTRACTING KEYWORDS FROM TRANSCRIPT")
    print("=" * 60)
    keywords = extract_key_phrases(transcript, max_k=max_keywords)
    print(f"[INFO] Extracted keywords: {keywords}")
    
    # Build soundbite
    print("\n" + "=" * 60)
    print("GENERATING SOUNDBITE")
    print("=" * 60)
    
    final_audio = AudioSegment.silent(duration=0)
    successful_clips = 0

    for keyword in keywords:
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
    print(f"[INFO] Clips used: {successful_clips}/{len(keywords)}")
    print("=" * 60)
    
    return output_file


if __name__ == "__main__":
    # Example usage
    sample_transcript = """
    So today was really tiring. I woke up late and missed my alarm, 
    so I had to rush to get ready. Then I realized I forgot my keys 
    and had to run back home. It was raining too which made everything worse. 
    By the time I reached the office I was completely stressed and exhausted.
    """
    
    transcript_to_soundbite(sample_transcript, output_file="my_day.ogg", max_keywords=8)