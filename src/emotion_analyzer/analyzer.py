# -*- coding: utf-8 -*-
"""
VNova Assistant - 视觉小说制作助手
情感分析模块 - 使用NLP技术对文本进行情感分析
"""

try:
    from snownlp import SnowNLP
except ImportError:
    print("Warning: snownlp library not found. Emotion analysis will not work.")
    print("Please install it using: pip install snownlp")
    SnowNLP = None

class EmotionAnalyzer:
    """Analyzes the emotion of a given text string."""
    def __init__(self):
        if SnowNLP is None:
            print("EmotionAnalyzer disabled because snownlp is not installed.")

    def analyze_emotion(self, text):
        """Analyzes the sentiment of the text.

        Args:
            text (str): The Chinese text to analyze.

        Returns:
            float: A sentiment score between 0 (negative) and 1 (positive),
                   or None if snownlp is not available or analysis fails.
        """
        if SnowNLP is None or not text:
            return None

        try:
            s = SnowNLP(text)
            # The sentiments method returns a score indicating positivity.
            sentiment_score = s.sentiments
            # You could potentially map this score to categories like
            # 'positive', 'negative', 'neutral' based on thresholds.
            # For now, returning the raw score.
            # Example mapping:
            # if sentiment_score > 0.6:
            #     return "positive"
            # elif sentiment_score < 0.4:
            #     return "negative"
            # else:
            #     return "neutral"
            return sentiment_score
        except Exception as e:
            print(f"Error during emotion analysis for text '{text[:50]}...': {e}")
            return None

# Example Usage (for testing)
if __name__ == '__main__':
    if SnowNLP:
        analyzer = EmotionAnalyzer()
        texts_to_analyze = [
            "今天天气真好，阳光明媚！",
            "我感到非常难过和失望。",
            "这部电影真是太无聊了。",
            "这只是一个普通的陈述句。",
            "",
            None
        ]

        for text in texts_to_analyze:
            if text is not None:
                score = analyzer.analyze_emotion(text)
                print(f'Text: "{text}" -> Sentiment Score: {score}')
            else:
                 print(f'Text: None -> Sentiment Score: {analyzer.analyze_emotion(text)}')
    else:
        print("Skipping emotion analysis test because snownlp is not installed.")