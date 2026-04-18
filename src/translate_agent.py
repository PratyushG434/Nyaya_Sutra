from sarvamai import SarvamAI
from typing import Optional, Literal


class TranslateAgent:
    
    def __init__(self, api_subscription_key: str):
        self.client = SarvamAI(api_subscription_key="sk_8tpjc8ai_khWfUZIEgN2sc8eqARMscwUU")
    
    def translate(
        self,
        text: str,
        source_language_code: str = "en-IN",
        target_language_code: str = "hi-IN",
        speaker_gender: Literal["Male", "Female", "Neutral"] = "Male",
        mode: Literal["formal", "modern-colloquial", "classical-colloquial", "code-mixed"] = "formal",
        model: str = "mayura:v1",
        enable_preprocessing: bool = False,
        numerals_format: Literal["native", "international"] = "native"
    ) -> str:
        """
        Translate text from source language to target language.
        
        Args:
            text: Input text to translate (can be mixed language)
            source_language_code: Source language code (e.g., "en-IN", "hi-IN", "ta-IN", "te-IN")
            target_language_code: Target language code
            speaker_gender: Gender for translation context
            mode: Translation style
                - formal: Professional/formal tone
                - modern-colloquial: Contemporary casual speech
                - classical-colloquial: Traditional casual speech
                - code-mixed: Mixed language output
            model: Translation model to use
            enable_preprocessing: Whether to preprocess input text
            numerals_format: Number format
                - native: Use native script numerals (e.g., "४५,०००")
                - international: Use Arabic numerals (e.g., "45,000")
        
        Returns:
            Translated text
        """
        response = self.client.text.translate(
            input=text,
            source_language_code=source_language_code,
            target_language_code=target_language_code,
            speaker_gender=speaker_gender,
            mode=mode,
            model=model,
            enable_preprocessing=enable_preprocessing,
            numerals_format=numerals_format
        )
        
        return response
    
    def translate_batch(
        self,
        texts: list[str],
        source_language_code: str = "en-IN",
        target_language_code: str = "hi-IN",
        **kwargs
    ) -> list[str]:
        """
        Translate multiple texts with the same settings.
        
        Args:
            texts: List of texts to translate
            source_language_code: Source language code
            target_language_code: Target language code
            **kwargs: Additional translation parameters
        
        Returns:
            List of translated texts
        """
        results = []
        for text in texts:
            translated = self.translate(
                text=text,
                source_language_code=source_language_code,
                target_language_code=target_language_code,
                **kwargs
            )
            results.append(translated)
        
        return results

