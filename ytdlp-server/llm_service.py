"""
LLM Service for AI Summarization

Supports multiple LLM providers:
- OpenAI (GPT-4o, GPT-4o-mini) + Whisper
- Anthropic (Claude)
- Google (Gemini)
"""

import os
import yaml
import logging
import base64
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


def load_config(config_path: str = "/app/config.yaml") -> Dict[str, Any]:
    """Load configuration from YAML file"""
    # Try multiple paths for development and production
    paths_to_try = [
        config_path,
        os.path.join(os.path.dirname(__file__), "..", "config.yaml"),
        os.path.join(os.path.dirname(__file__), "config.yaml"),
    ]

    for path in paths_to_try:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)

    logger.warning("Config file not found, using defaults")
    return {
        "llm": {
            "default_provider": "openai",
            "output_language": "ko",
            "providers": {}
        },
        "summarization": {
            "max_transcript_length": 100000,
            "prompts": {
                "ko": "다음 내용을 요약해주세요:\n{content}",
                "en": "Please summarize the following:\n{content}"
            }
        }
    }


class LLMProvider(ABC):
    """Abstract base class for LLM providers"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.api_key = self._get_api_key()

    def _get_api_key(self) -> Optional[str]:
        """Get API key from environment variable"""
        env_var = self.config.get("api_key_env", "")
        return os.environ.get(env_var)

    @property
    def is_available(self) -> bool:
        """Check if provider is available (API key is set)"""
        return bool(self.api_key)

    @abstractmethod
    def summarize_text(self, text: str, prompt_template: str, model: str) -> Dict[str, Any]:
        """Summarize text content"""
        pass

    def transcribe_audio(self, audio_path: str) -> Dict[str, Any]:
        """Transcribe audio to text (optional, not all providers support this)"""
        return {"error": "Audio transcription not supported by this provider"}

    def summarize_audio_multimodal(self, audio_path: str, prompt: str, model: str) -> Dict[str, Any]:
        """Summarize audio directly using multimodal capabilities"""
        return {"error": "Multimodal audio not supported by this provider"}

    def get_models(self) -> List[Dict[str, Any]]:
        """Get available models for this provider"""
        return self.config.get("models", [])


class OpenAIProvider(LLMProvider):
    """OpenAI provider (GPT-4o, GPT-4o-mini, Whisper)"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self._client = None

    @property
    def client(self):
        if self._client is None and self.is_available:
            from openai import OpenAI
            self._client = OpenAI(api_key=self.api_key)
        return self._client

    def summarize_text(self, text: str, prompt_template: str, model: str = "gpt-4o-mini") -> Dict[str, Any]:
        if not self.is_available:
            return {"error": "OpenAI API key not configured"}

        try:
            prompt = prompt_template.format(content=text)
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that summarizes video content."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=4096
            )
            return {
                "success": True,
                "summary": response.choices[0].message.content,
                "model": model,
                "tokens_used": response.usage.total_tokens if response.usage else 0
            }
        except Exception as e:
            logger.error(f"OpenAI summarization error: {e}")
            return {"error": str(e)}

    def transcribe_audio(self, audio_path: str) -> Dict[str, Any]:
        if not self.is_available:
            return {"error": "OpenAI API key not configured"}

        whisper_model = self.config.get("whisper_model", "whisper-1")

        try:
            with open(audio_path, "rb") as audio_file:
                response = self.client.audio.transcriptions.create(
                    model=whisper_model,
                    file=audio_file,
                    response_format="text"
                )
            return {
                "success": True,
                "transcription": response,
                "model": whisper_model
            }
        except Exception as e:
            logger.error(f"Whisper transcription error: {e}")
            return {"error": str(e)}

    def summarize_audio_multimodal(self, audio_path: str, prompt: str, model: str = "gpt-4o") -> Dict[str, Any]:
        if not self.is_available:
            return {"error": "OpenAI API key not configured"}

        # Check if model supports audio
        model_config = next((m for m in self.get_models() if m["id"] == model), None)
        if not model_config or not model_config.get("supports_audio", False):
            return {"error": f"Model {model} does not support audio input"}

        try:
            with open(audio_path, "rb") as f:
                audio_data = base64.b64encode(f.read()).decode('utf-8')

            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "input_audio",
                                "input_audio": {
                                    "data": audio_data,
                                    "format": "mp3"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=4096
            )
            return {
                "success": True,
                "summary": response.choices[0].message.content,
                "model": model,
                "tokens_used": response.usage.total_tokens if response.usage else 0
            }
        except Exception as e:
            logger.error(f"OpenAI multimodal error: {e}")
            return {"error": str(e)}


class AnthropicProvider(LLMProvider):
    """Anthropic provider (Claude)"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self._client = None

    @property
    def client(self):
        if self._client is None and self.is_available:
            from anthropic import Anthropic
            self._client = Anthropic(api_key=self.api_key)
        return self._client

    def summarize_text(self, text: str, prompt_template: str, model: str = "claude-sonnet-4-20250514") -> Dict[str, Any]:
        if not self.is_available:
            return {"error": "Anthropic API key not configured"}

        try:
            prompt = prompt_template.format(content=text)
            response = self.client.messages.create(
                model=model,
                max_tokens=4096,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            return {
                "success": True,
                "summary": response.content[0].text,
                "model": model,
                "tokens_used": response.usage.input_tokens + response.usage.output_tokens if response.usage else 0
            }
        except Exception as e:
            logger.error(f"Anthropic summarization error: {e}")
            return {"error": str(e)}


class GoogleProvider(LLMProvider):
    """Google provider (Gemini)"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self._client = None

    @property
    def client(self):
        if self._client is None and self.is_available:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self._client = genai
        return self._client

    def summarize_text(self, text: str, prompt_template: str, model: str = "gemini-2.0-flash") -> Dict[str, Any]:
        if not self.is_available:
            return {"error": "Google API key not configured"}

        try:
            prompt = prompt_template.format(content=text)
            gemini_model = self.client.GenerativeModel(model)
            response = gemini_model.generate_content(prompt)
            return {
                "success": True,
                "summary": response.text,
                "model": model,
                "tokens_used": 0  # Gemini doesn't always return token count
            }
        except Exception as e:
            logger.error(f"Google summarization error: {e}")
            return {"error": str(e)}

    def summarize_audio_multimodal(self, audio_path: str, prompt: str, model: str = "gemini-2.0-flash") -> Dict[str, Any]:
        if not self.is_available:
            return {"error": "Google API key not configured"}

        # Check if model supports audio
        model_config = next((m for m in self.get_models() if m["id"] == model), None)
        if not model_config or not model_config.get("supports_audio", False):
            return {"error": f"Model {model} does not support audio input"}

        try:
            # Upload audio file
            audio_file = self.client.upload_file(audio_path)

            gemini_model = self.client.GenerativeModel(model)
            response = gemini_model.generate_content([prompt, audio_file])

            return {
                "success": True,
                "summary": response.text,
                "model": model,
                "tokens_used": 0
            }
        except Exception as e:
            logger.error(f"Google multimodal error: {e}")
            return {"error": str(e)}


class LLMService:
    """Main LLM service that manages providers"""

    def __init__(self, config_path: str = "/app/config.yaml"):
        self.config = load_config(config_path)
        self.llm_config = self.config.get("llm", {})
        self.summarization_config = self.config.get("summarization", {})
        self._providers: Dict[str, LLMProvider] = {}

    def _get_provider(self, provider_name: str) -> Optional[LLMProvider]:
        """Get or create a provider instance"""
        if provider_name not in self._providers:
            provider_config = self.llm_config.get("providers", {}).get(provider_name, {})

            if provider_name == "openai":
                self._providers[provider_name] = OpenAIProvider(provider_config)
            elif provider_name == "anthropic":
                self._providers[provider_name] = AnthropicProvider(provider_config)
            elif provider_name == "google":
                self._providers[provider_name] = GoogleProvider(provider_config)
            else:
                return None

        return self._providers.get(provider_name)

    def get_provider_status(self) -> Dict[str, bool]:
        """Get availability status of all providers"""
        status = {}
        for provider_name in ["openai", "anthropic", "google"]:
            provider = self._get_provider(provider_name)
            status[provider_name] = provider.is_available if provider else False
        return status

    def get_available_providers(self) -> List[Dict[str, Any]]:
        """Get list of available providers with their models"""
        providers = []
        for provider_name in ["openai", "anthropic", "google"]:
            provider = self._get_provider(provider_name)
            if provider:
                providers.append({
                    "id": provider_name,
                    "name": provider_name.capitalize(),
                    "available": provider.is_available,
                    "models": provider.get_models()
                })
        return providers

    def get_prompt(self, language: str = None) -> str:
        """Get summarization prompt for specified language"""
        if language is None:
            language = self.llm_config.get("output_language", "ko")

        prompts = self.summarization_config.get("prompts", {})
        return prompts.get(language, prompts.get("ko", "{content}"))

    def summarize_transcript(
        self,
        text: str,
        provider: str = None,
        model: str = None,
        language: str = None
    ) -> Dict[str, Any]:
        """Summarize transcript text"""
        if provider is None:
            provider = self.llm_config.get("default_provider", "openai")

        llm_provider = self._get_provider(provider)
        if not llm_provider:
            return {"error": f"Unknown provider: {provider}"}

        if not llm_provider.is_available:
            return {"error": f"Provider {provider} is not configured (missing API key)"}

        # Get default model if not specified
        if model is None:
            models = llm_provider.get_models()
            model = models[0]["id"] if models else None

        if not model:
            return {"error": f"No model specified for provider {provider}"}

        # Truncate text if too long
        max_length = self.summarization_config.get("max_transcript_length", 100000)
        if len(text) > max_length:
            text = text[:max_length] + "\n\n[Truncated due to length...]"

        prompt_template = self.get_prompt(language)
        return llm_provider.summarize_text(text, prompt_template, model)

    def transcribe_audio(self, audio_path: str, provider: str = "openai") -> Dict[str, Any]:
        """Transcribe audio using Whisper (OpenAI only)"""
        llm_provider = self._get_provider(provider)
        if not llm_provider:
            return {"error": f"Unknown provider: {provider}"}

        return llm_provider.transcribe_audio(audio_path)

    def summarize_audio(
        self,
        audio_path: str,
        mode: str = "whisper",  # "whisper" or "multimodal"
        provider: str = None,
        model: str = None,
        language: str = None
    ) -> Dict[str, Any]:
        """Summarize audio content"""
        if provider is None:
            provider = self.llm_config.get("default_provider", "openai")

        llm_provider = self._get_provider(provider)
        if not llm_provider:
            return {"error": f"Unknown provider: {provider}"}

        if not llm_provider.is_available:
            return {"error": f"Provider {provider} is not configured (missing API key)"}

        # Get default model if not specified
        if model is None:
            models = llm_provider.get_models()
            # For multimodal, prefer audio-capable model
            if mode == "multimodal":
                audio_models = [m for m in models if m.get("supports_audio", False)]
                model = audio_models[0]["id"] if audio_models else (models[0]["id"] if models else None)
            else:
                model = models[0]["id"] if models else None

        if not model:
            return {"error": f"No model specified for provider {provider}"}

        prompt_template = self.get_prompt(language)
        prompt = prompt_template.replace("{content}", "the audio content provided")

        if mode == "multimodal":
            return llm_provider.summarize_audio_multimodal(audio_path, prompt, model)
        else:
            # Whisper mode: transcribe first, then summarize
            # Use OpenAI for transcription regardless of summary provider
            openai_provider = self._get_provider("openai")
            if not openai_provider or not openai_provider.is_available:
                return {"error": "OpenAI API key required for Whisper transcription"}

            transcription_result = openai_provider.transcribe_audio(audio_path)
            if "error" in transcription_result:
                return transcription_result

            transcription = transcription_result.get("transcription", "")
            summary_result = self.summarize_transcript(transcription, provider, model, language)

            if "error" in summary_result:
                return summary_result

            return {
                "success": True,
                "summary": summary_result.get("summary", ""),
                "transcription": transcription,
                "model": summary_result.get("model", model),
                "tokens_used": summary_result.get("tokens_used", 0)
            }
