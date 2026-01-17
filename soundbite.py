import os
import random
import requests
from pydub import AudioSegment
from pydub.effects import normalize
from dotenv import load_dotenv
import time

load_dotenv()

FREESOUND_API_KEY = os.getenv("FREESOUND_API_KEY")
BASE_URL = "https://freesound.org/apiv2/search/text/"

# Enhanced keyword mapping - maps user keywords to better search terms
KEYWORD_MAPPING = {
    "alarm": "alarm clock beeping",
    "snore": "snoring heavy",
    "snoring": "snoring",
    "panic": "scream panic",
    "shower": "shower running",
    "eww": "disgust ew",
    "door": "door close",
    "car": "car engine start",
    "phone": "phone ringing",
    "footsteps": "footsteps walking",
    "walking": "footsteps",
    "laugh": "laughing",
    "giggle": "giggle",
    "cry": "crying sobbing",
    "explosion": "explosion bomb",
    "gunshot": "gunshot pistol",
    "dog": "dog barking",
    "cat": "cat meowing",
    "rain": "rain rainfall",
    "thunder": "thunder storm",
    "wind": "wind blowing",
    "fire": "fire crackling",
    "glass": "glass breaking shatter",
    "water": "water flowing",
    "bell": "bell ringing",
    "whistle": "whistle blow",
}

MIN_DURATION = 0.3
MAX_DURATION = 5.0
TARGET_CLIP_LENGTH_MS = 2000
SILENCE_MS = 120


def normalize_keyword(keyword):
    """Convert keyword to optimized search term"""
    keyword_lower = keyword.lower().strip()
    return KEYWORD_MAPPING.get(keyword_lower, keyword_lower)


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
        "sort": "downloads_desc",  # Most downloaded = best quality
        "fields": "id,name,previews,duration,download,num_downloads,avg_rating,tags",
        "page_size": 30
    }
    
    headers = {
        "Authorization": f"Token {FREESOUND_API_KEY}"
    }
    
    try:
        print(f"[DEBUG] Searching Freesound for: '{search_term}'")
        response = requests.get(BASE_URL, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        sounds = data.get("results", [])
        
        if sounds:
            print(f"[INFO] Found {len(sounds)} sounds for '{keyword}'")
        else:
            print(f"[WARN] No sounds found for '{keyword}'")
        
        return sounds
        
    except Exception as e:
        print(f"[ERROR] Freesound search failed: {e}")
        return []


def score_sound(sound, keyword):
    """Score a sound based on relevance and quality"""
    score = 0
    
    # Downloads (0-40 points) - popular sounds are usually good
    downloads = sound.get("num_downloads", 0)
    score += min(downloads / 100, 40)
    
    # Rating (0-25 points)
    rating = sound.get("avg_rating", 0)
    score += rating * 5
    
    # Duration preference (0-25 points) - prefer shorter, punchier sounds
    duration = sound.get("duration", 10)
    if duration <= 1.5:
        score += 25
    elif duration <= 2.5:
        score += 18
    elif duration <= 4:
        score += 10
    else:
        score += 5
    
    # Keyword matching in name/tags (0-10 points)
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
        # Use high-quality preview MP3
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
        return None
    
    # Score and sort sounds
    scored_sounds = [(score_sound(s, keyword), s) for s in sounds]
    scored_sounds.sort(reverse=True, key=lambda x: x[0])
    
    # Try top 5 sounds in case download/processing fails
    for score, sound in scored_sounds[:5]:
        print(f"[DEBUG] Trying '{sound['name'][:40]}' (score: {score:.1f}, downloads: {sound.get('num_downloads', 0)})")
        
        filepath = download_sound(sound)
        if not filepath:
            continue
        
        audio = process_sound(filepath)
        
        # Cleanup
        if os.path.exists(filepath):
            os.remove(filepath)
        
        if audio:
            time.sleep(0.3)  # Rate limiting
            return audio
    
    return None


def build_soundbite_message(keywords, output_file="output.ogg"):
    """Build soundbite from keywords"""
    if not FREESOUND_API_KEY:
        print("=" * 60)
        print("SETUP REQUIRED")
        print("=" * 60)
        print("\n1. Get FREE API key at: https://freesound.org/apiv2/apply/")
        print("\n2. Add to your .env file:")
        print("   FREESOUND_API_KEY=your_api_key_here")
        print("\n3. Run this script again")
        print("=" * 60)
        return
    
    final_audio = AudioSegment.silent(duration=0)
    successful_clips = 0

    for keyword in keywords:
        print(f"\n{'='*60}")
        print(f"Processing: '{keyword}'")
        print('='*60)
        
        clip = keyword_to_audio(keyword)
        if clip:
            final_audio += clip
            final_audio += AudioSegment.silent(duration=SILENCE_MS)
            successful_clips += 1
        else:
            print(f"[SKIP] Could not get audio for '{keyword}'")

    if len(final_audio) == 0:
        print("\n[ERROR] No audio clips were generated.")
        return

    # Export
    final_audio.export(
        output_file,
        format="ogg",
        codec="libopus",
        parameters=["-ac", "1"]
    )

    print(f"\n{'='*60}")
    print(f"[OK] Exported {output_file}")
    print(f"[INFO] Duration: {len(final_audio)/1000:.2f}s")
    print(f"[INFO] Successful clips: {successful_clips}/{len(keywords)}")
    print('='*60)


if __name__ == "__main__":
    # Test with diverse keywords
    keywords =  ['japan', 'friends', 'big fight', 'someone', 'shower', 'smelly', 'shoes']
    build_soundbite_message(keywords)