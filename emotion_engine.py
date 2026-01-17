from nrclex import NRCLex
from textblob import TextBlob
import re
from collections import defaultdict


class EmotionEngine:
    """
    1. Text preprocessing (remove filler words from speech transcription)
    2. NRCLex emotion scoring (lexicon lookup)
    3. TextBlob sentiment analysis (polarity check)
    4. Confidence-based decision logic with fallback handling
    """
    
    def __init__(self):
        """Initialize the engine with emotion-to-emoji mappings."""
        
        # Emotion -> Telegram Emoji mapping
        self.emotion_emoji_map = {
            'joy': '😁',
            'love': '❤️',
            'anger': '🤬',
            'sadness': '😢',
            'fear': '😨',
            'surprise': '🤯',
            'disgust': '🤮',
            'neutral': '👍',
        }
        
        # Speech-specific filler words (common in voice transcriptions)
        self.filler_words = [
            'um', 'uh', 'like', 'you know', 'i mean', 'sort of', 
            'kind of', 'actually', 'basically', 'literally'
        ]
        
        # Confidence threshold for emotion detection
        self.confidence_threshold = 0.15  # Minimum score to consider valid
        
    def preprocess_text(self, text: str) -> str:
        """
        Clean transcribed speech text for better emotion detection.
        
        Args:
            text: Raw transcription from speech recognition
            
        Returns:
            Cleaned text ready for emotion analysis
        """
        # Convert to lowercase
        text = text.lower()
        
        # Remove filler words common in speech
        for filler in self.filler_words:
            text = re.sub(r'\b' + filler + r'\b', '', text, flags=re.IGNORECASE)
        
        # Normalize whitespace
        text = ' '.join(text.split())
        
        return text
    
    def extract_emotions(self, text: str) -> dict:
        """
        Extract emotion scores using NRCLex lexicon.
        
        Technical Details:
        - NRCLex uses the NRC Emotion Lexicon (14,182 words)
        - Each word is pre-labeled with 8 basic emotions + 2 sentiments
        - Returns normalized frequency scores
        
        Args:
            text: Preprocessed text
            
        Returns:
            Dictionary of {emotion: score} pairs
        """
        # Create NRCLex emotion object
        emotion_obj = NRCLex(text)
        
        # Get raw emotion scores (word frequency counts)
        raw_scores = emotion_obj.affect_frequencies
        
        # Filter to only emotions we care about
        relevant_emotions = ['joy', 'anger', 'sadness', 'fear', 'surprise', 'disgust']
        filtered_scores = {k: v for k, v in raw_scores.items() if k in relevant_emotions}
        
        return filtered_scores
    
    def get_sentiment_boost(self, text: str) -> str:
        """
        Use TextBlob sentiment analysis as a secondary signal.
        Helps disambiguate between similar emotion scores.
        
        Args:
            text: Preprocessed text
            
        Returns:
            Suggested emotion based on sentiment polarity
        """
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity  # Range: -1 (negative) to +1 (positive)
        
        if polarity > 0.5:
            return 'joy'
        elif polarity < -0.5:
            # Negative sentiment could be anger or sadness
            # Check for intensity words to distinguish
            if any(word in text.lower() for word in ['hate', 'angry', 'furious', 'stupid']):
                return 'anger'
            else:
                return 'sadness'
        else:
            return 'neutral'
    
    def decide_emotion(self, emotion_scores: dict, text: str) -> str:
        """
        Decision logic to select final emotion from multiple signals.
        
        Algorithm:
        1. Check if any emotion exceeds confidence threshold
        2. If multiple emotions are tied, use sentiment analysis as tiebreaker
        3. If no clear emotion, default to neutral
        
        Args:
            emotion_scores: Dictionary of emotion scores from NRCLex
            text: Original text (for sentiment analysis)
            
        Returns:
            Single emotion label (string)
        """
        # Handle empty or very low scores
        if not emotion_scores or max(emotion_scores.values(), default=0) < self.confidence_threshold:
            # Fallback to sentiment analysis
            return self.get_sentiment_boost(text)
        
        # Get top emotion
        top_emotion = max(emotion_scores, key=emotion_scores.get)
        top_score = emotion_scores[top_emotion]
        
        # Check if there's a close second (within 10% of top score)
        sorted_emotions = sorted(emotion_scores.items(), key=lambda x: x[1], reverse=True)
        
        if len(sorted_emotions) > 1:
            second_emotion, second_score = sorted_emotions[1]
            
            # If scores are very close, use sentiment to break tie
            if abs(top_score - second_score) < 0.1:
                sentiment_hint = self.get_sentiment_boost(text)
                
                # Prefer sentiment hint if it matches one of the top contenders
                if sentiment_hint == top_emotion or sentiment_hint == second_emotion:
                    return sentiment_hint
        
        return top_emotion
    
    def detect_emotion(self, text: str) -> str:
        """
        Main public method: Detect emotion from text and return emoji.
        
        Full Pipeline:
        1. Preprocess text (remove fillers)
        2. Extract emotion scores (NRCLex)
        3. Apply decision logic (handle ties/neutral)
        4. Map emotion to emoji
        
        Args:
            text: Raw transcription from speech recognition
            
        Returns:
            Telegram emoji string (e.g., '😂', '😡', '👍')
        """
        # Step 1: Preprocess
        cleaned_text = self.preprocess_text(text)
        
        # Handle edge case: empty text after preprocessing
        if not cleaned_text.strip():
            return self.emotion_emoji_map['neutral']
        
        # Step 2: Extract emotions
        emotion_scores = self.extract_emotions(cleaned_text)
        
        # Step 3: Decide final emotion
        final_emotion = self.decide_emotion(emotion_scores, cleaned_text)
        
        # Step 4: Map to emoji
        emoji = self.emotion_emoji_map.get(final_emotion, self.emotion_emoji_map['neutral'])
        
        return emoji
    
    def get_detailed_analysis(self, text: str) -> dict:
        """
        Optional: Get full breakdown for debugging/demo purposes.
        
        Useful for explaining to judges how the engine works.
        
        Args:
            text: Raw transcription
            
        Returns:
            Dictionary with all intermediate results
        """
        cleaned_text = self.preprocess_text(text)
        emotion_scores = self.extract_emotions(cleaned_text)
        final_emotion = self.decide_emotion(emotion_scores, cleaned_text)
        emoji = self.emotion_emoji_map.get(final_emotion, self.emotion_emoji_map['neutral'])
        
        # Get sentiment for comparison
        blob = TextBlob(cleaned_text)
        
        return {
            'original_text': text,
            'cleaned_text': cleaned_text,
            'emotion_scores': emotion_scores,
            'final_emotion': final_emotion,
            'emoji': emoji,
            'sentiment_polarity': blob.sentiment.polarity,
            'sentiment_subjectivity': blob.sentiment.subjectivity,
        }


# Example usage
if __name__ == "__main__":
    engine = EmotionEngine()
    
    # Test cases
    test_texts = [
        "I'm so happy and excited about this!",
        "This is absolutely terrible and I hate it",
        "I'm scared and worried about what might happen",
        "Wow, I can't believe this happened!",
        "Um, like, I guess this is okay, you know",
    ]
    
    print("=" * 60)
    print("EMOTION ENGINE TEST RESULTS")
    print("=" * 60)
    
    for text in test_texts:
        emoji = engine.detect_emotion(text)
        analysis = engine.get_detailed_analysis(text)
        
        print(f"\nText: {text}")
        print(f"Emoji: {emoji}")
        print(f"Emotion: {analysis['final_emotion']}")
        print(f"Scores: {analysis['emotion_scores']}")
        print("-" * 60)