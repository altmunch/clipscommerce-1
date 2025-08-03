"""
Text-to-Speech services for video generation
"""

import abc
import asyncio
import logging
import uuid
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum
import aiohttp
import io
import wave

from app.core.config import settings

logger = logging.getLogger(__name__)


class VoiceGender(Enum):
    """Voice gender options"""
    MALE = "male"
    FEMALE = "female"
    NEUTRAL = "neutral"


class VoiceAge(Enum):
    """Voice age ranges"""
    YOUNG = "young"      # 20-30
    MIDDLE = "middle"    # 30-50
    MATURE = "mature"    # 50+


class EmotionType(Enum):
    """Voice emotion types"""
    NEUTRAL = "neutral"
    HAPPY = "happy"
    SAD = "sad"
    EXCITED = "excited"
    CALM = "calm"
    PROFESSIONAL = "professional"
    FRIENDLY = "friendly"
    ENERGETIC = "energetic"


@dataclass
class VoiceSettings:
    """Voice configuration settings"""
    voice_id: str
    stability: float = 0.75    # Voice consistency (0.0 - 1.0)
    clarity: float = 0.75      # Voice clarity (0.0 - 1.0)
    style: float = 0.0         # Style enhancement (0.0 - 1.0)
    speed: float = 1.0         # Speech speed multiplier
    pitch: float = 0.0         # Pitch adjustment (-1.0 to 1.0)
    emotion: EmotionType = EmotionType.NEUTRAL


@dataclass
class TTSRequest:
    """Text-to-speech request"""
    text: str
    voice_settings: VoiceSettings
    output_format: str = "mp3"
    sample_rate: int = 22050
    model_id: str = "eleven_monolingual_v1"


@dataclass
class TTSResult:
    """Text-to-speech result"""
    audio_url: str
    duration: float
    file_size: int
    format: str
    sample_rate: int
    cost: float = 0.0
    generation_time: float = 0.0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class BaseTTSProvider(abc.ABC):
    """Base class for text-to-speech providers"""
    
    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url
        self.session: Optional[aiohttp.ClientSession] = None
        self.cost_per_character = 0.0001  # Base cost per character
    
    async def __aenter__(self):
        timeout = aiohttp.ClientTimeout(total=300)  # 5 minute timeout
        self.session = aiohttp.ClientSession(timeout=timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    @abc.abstractmethod
    async def generate_speech(self, request: TTSRequest) -> TTSResult:
        """Generate speech from text"""
        pass
    
    @abc.abstractmethod
    async def get_available_voices(self) -> List[Dict[str, Any]]:
        """Get list of available voices"""
        pass
    
    @abc.abstractmethod
    def estimate_cost(self, text: str) -> float:
        """Estimate cost for generating speech"""
        pass
    
    def _calculate_duration(self, text: str, speed: float = 1.0) -> float:
        """Estimate speech duration based on text length"""
        # Average speaking rate: ~150 words per minute
        words = len(text.split())
        minutes = words / (150 * speed)
        return minutes * 60  # Convert to seconds


class ElevenLabsProvider(BaseTTSProvider):
    """ElevenLabs text-to-speech provider"""
    
    def __init__(self, api_key: Optional[str] = None):
        api_key = api_key or getattr(settings, 'ELEVENLABS_API_KEY', '')
        super().__init__(api_key, "https://api.elevenlabs.io/v1")
        self.cost_per_character = 0.00003  # ElevenLabs pricing
        
        # Popular voice IDs
        self.default_voices = {
            "rachel": "21m00Tcm4TlvDq8ikWAM",  # Female, young, American
            "drew": "29vD33N1CtxCmqQRPOHJ",    # Male, middle-aged, American
            "clyde": "2EiwWnXFnvU5JabPnv8n",   # Male, middle-aged, American
            "paul": "5Q0t7uMcjvnagumLfvZi",    # Male, middle-aged, American
            "domi": "AZnzlk1XvdvUeBnXmlld",    # Female, young, American
            "dave": "CYw3kZ02Hs0563khs1Fj",    # Male, young, British
            "fin": "D38z5RcWu1voky8WS1ja",     # Male, old, Irish
            "sarah": "EXAVITQu4vr4xnSDxMaL",   # Female, young, American
            "antoni": "ErXwobaYiN019PkySvjV",  # Male, young, American
            "thomas": "GBv7mTt0atIp3Br8iCZE",  # Male, mature, American
            "charlie": "IKne3meq5aSn9XLyUdCD", # Male, middle-aged, Australian
            "george": "JBFqnCBsd6RMkjVDRZzb",  # Male, middle-aged, British
            "emily": "LcfcDJNUP1GQjkzn1xUU",   # Female, young, American
            "elli": "MF3mGyEYCl7XYWbV9V6O",    # Female, young, American
            "callum": "N2lVS1w4EtoT3dr4eOWO",  # Male, middle-aged, American
            "patrick": "ODq5zmih8GrVes37Dizd", # Male, middle-aged, American
            "harry": "SOYHLrjzK2X1ezoPC6cr",   # Male, young, American
            "liam": "TX3LPaxmHKxFdv7VOQHJ",    # Male, young, American
            "dorothy": "ThT5KcBeYPX3keUQqHPh", # Female, young, British
            "josh": "TxGEqnHWrfWFTfGW9XjX",    # Male, young, American
            "arnold": "VR6AewLTigWG4xSOukaG", # Male, mature, American
            "adam": "pNInz6obpgDQGcFmaJgB",    # Male, middle-aged, American
            "sam": "yoZ06aMxZJJ28mfd3POQ"      # Male, young, American
        }
    
    async def generate_speech(self, request: TTSRequest) -> TTSResult:
        """Generate speech using ElevenLabs API"""
        if not self.api_key:
            raise ValueError("ElevenLabs API key not configured")
        
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.api_key
        }
        
        # Map our settings to ElevenLabs format
        voice_settings = {
            "stability": request.voice_settings.stability,
            "similarity_boost": request.voice_settings.clarity,
            "style": request.voice_settings.style,
            "use_speaker_boost": True
        }
        
        payload = {
            "text": request.text,
            "model_id": request.model_id,
            "voice_settings": voice_settings
        }
        
        voice_id = request.voice_settings.voice_id
        url = f"{self.base_url}/text-to-speech/{voice_id}"
        
        try:
            start_time = asyncio.get_event_loop().time()
            
            async with self.session.post(url, json=payload, headers=headers) as response:
                response.raise_for_status()
                
                audio_data = await response.read()
                generation_time = asyncio.get_event_loop().time() - start_time
                
                # In production, upload to cloud storage
                audio_url = f"https://mock-storage.com/audio/{uuid.uuid4()}.mp3"
                
                # Estimate duration
                duration = self._calculate_duration(request.text, request.voice_settings.speed)
                
                return TTSResult(
                    audio_url=audio_url,
                    duration=duration,
                    file_size=len(audio_data),
                    format=request.output_format,
                    sample_rate=request.sample_rate,
                    cost=self.estimate_cost(request.text),
                    generation_time=generation_time,
                    metadata={
                        "provider": "elevenlabs",
                        "voice_id": voice_id,
                        "model_id": request.model_id,
                        "characters": len(request.text)
                    }
                )
                
        except aiohttp.ClientError as e:
            logger.error(f"ElevenLabs TTS failed: {e}")
            raise
    
    async def get_available_voices(self) -> List[Dict[str, Any]]:
        """Get available ElevenLabs voices"""
        if not self.api_key:
            return []
        
        headers = {"xi-api-key": self.api_key}
        
        try:
            async with self.session.get(f"{self.base_url}/voices", headers=headers) as response:
                response.raise_for_status()
                data = await response.json()
                
                voices = []
                for voice in data.get("voices", []):
                    voices.append({
                        "voice_id": voice["voice_id"],
                        "name": voice["name"],
                        "gender": self._detect_gender(voice["name"]),
                        "accent": voice.get("labels", {}).get("accent", "american"),
                        "age": voice.get("labels", {}).get("age", "middle"),
                        "description": voice.get("labels", {}).get("description", ""),
                        "preview_url": voice.get("preview_url"),
                        "category": voice.get("category", "generated")
                    })
                
                return voices
                
        except aiohttp.ClientError as e:
            logger.error(f"Failed to get ElevenLabs voices: {e}")
            return []
    
    def _detect_gender(self, name: str) -> str:
        """Simple gender detection based on name"""
        male_names = {
            "drew", "clyde", "paul", "dave", "fin", "antoni", "thomas", 
            "charlie", "george", "callum", "patrick", "harry", "liam", 
            "josh", "arnold", "adam", "sam"
        }
        
        female_names = {
            "rachel", "domi", "sarah", "emily", "elli", "dorothy"
        }
        
        name_lower = name.lower()
        if name_lower in male_names:
            return "male"
        elif name_lower in female_names:
            return "female"
        else:
            return "neutral"
    
    def estimate_cost(self, text: str) -> float:
        """Estimate ElevenLabs cost"""
        characters = len(text)
        return characters * self.cost_per_character
    
    def get_voice_by_characteristics(
        self, 
        gender: VoiceGender = VoiceGender.NEUTRAL,
        age: VoiceAge = VoiceAge.MIDDLE,
        accent: str = "american"
    ) -> str:
        """Get voice ID by characteristics"""
        
        # Mapping of characteristics to voice IDs
        voice_map = {
            (VoiceGender.FEMALE, VoiceAge.YOUNG): "rachel",
            (VoiceGender.MALE, VoiceAge.YOUNG): "josh",
            (VoiceGender.FEMALE, VoiceAge.MIDDLE): "sarah",
            (VoiceGender.MALE, VoiceAge.MIDDLE): "drew",
            (VoiceGender.MALE, VoiceAge.MATURE): "arnold"
        }
        
        voice_name = voice_map.get((gender, age), "rachel")
        return self.default_voices.get(voice_name, self.default_voices["rachel"])


class BuiltInTTSProvider(BaseTTSProvider):
    """Built-in TTS provider using system voices"""
    
    def __init__(self):
        super().__init__("", "")
        self.cost_per_character = 0.0  # Free
    
    async def generate_speech(self, request: TTSRequest) -> TTSResult:
        """Generate speech using built-in TTS"""
        # Mock implementation - in production would use system TTS
        await asyncio.sleep(1)  # Simulate processing
        
        duration = self._calculate_duration(request.text, request.voice_settings.speed)
        audio_url = f"https://mock-storage.com/audio/{uuid.uuid4()}.mp3"
        
        return TTSResult(
            audio_url=audio_url,
            duration=duration,
            file_size=duration * 16000,  # Estimate based on sample rate
            format=request.output_format,
            sample_rate=request.sample_rate,
            cost=0.0,
            generation_time=1.0,
            metadata={
                "provider": "builtin",
                "voice_id": request.voice_settings.voice_id
            }
        )
    
    async def get_available_voices(self) -> List[Dict[str, Any]]:
        """Get built-in system voices"""
        return [
            {
                "voice_id": "system_male_1",
                "name": "System Male",
                "gender": "male",
                "accent": "neutral",
                "age": "middle",
                "description": "Built-in male voice"
            },
            {
                "voice_id": "system_female_1",
                "name": "System Female", 
                "gender": "female",
                "accent": "neutral",
                "age": "middle",
                "description": "Built-in female voice"
            }
        ]
    
    def estimate_cost(self, text: str) -> float:
        """Built-in TTS is free"""
        return 0.0


class TTSService:
    """Main TTS service that manages multiple providers"""
    
    def __init__(self):
        self.providers = {
            "elevenlabs": ElevenLabsProvider(),
            "builtin": BuiltInTTSProvider()
        }
        self.default_provider = "elevenlabs"
    
    async def generate_speech(
        self,
        text: str,
        voice_id: str = "21m00Tcm4TlvDq8ikWAM",  # ElevenLabs Rachel
        provider: str = None,
        voice_settings: Optional[VoiceSettings] = None,
        **kwargs
    ) -> TTSResult:
        """Generate speech using specified provider"""
        
        provider = provider or self.default_provider
        if provider not in self.providers:
            raise ValueError(f"Unknown TTS provider: {provider}")
        
        if voice_settings is None:
            voice_settings = VoiceSettings(voice_id=voice_id)
        
        request = TTSRequest(
            text=text,
            voice_settings=voice_settings,
            **kwargs
        )
        
        tts_provider = self.providers[provider]
        async with tts_provider:
            return await tts_provider.generate_speech(request)
    
    async def get_available_voices(self, provider: str = None) -> List[Dict[str, Any]]:
        """Get available voices from provider"""
        provider = provider or self.default_provider
        if provider not in self.providers:
            return []
        
        tts_provider = self.providers[provider]
        async with tts_provider:
            return await tts_provider.get_available_voices()
    
    def estimate_cost(self, text: str, provider: str = None) -> float:
        """Estimate TTS cost"""
        provider = provider or self.default_provider
        if provider not in self.providers:
            return 0.0
        
        return self.providers[provider].estimate_cost(text)
    
    async def generate_speech_for_segments(
        self,
        text_segments: List[str],
        voice_id: str = "21m00Tcm4TlvDq8ikWAM",
        provider: str = None
    ) -> List[TTSResult]:
        """Generate speech for multiple text segments"""
        
        tasks = []
        for text in text_segments:
            if text.strip():  # Skip empty segments
                task = self.generate_speech(
                    text=text,
                    voice_id=voice_id,
                    provider=provider
                )
                tasks.append(task)
        
        if not tasks:
            return []
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"TTS generation failed for segment {i}: {result}")
            else:
                valid_results.append(result)
        
        return valid_results
    
    def get_voice_recommendations(
        self,
        content_type: str = "professional",
        target_audience: str = "general",
        brand_voice: str = "friendly"
    ) -> List[Dict[str, Any]]:
        """Get voice recommendations based on content characteristics"""
        
        recommendations = []
        
        # Professional content voices
        if content_type == "professional":
            recommendations.extend([
                {
                    "voice_id": "21m00Tcm4TlvDq8ikWAM",  # Rachel
                    "name": "Rachel",
                    "reason": "Clear, professional female voice",
                    "provider": "elevenlabs"
                },
                {
                    "voice_id": "29vD33N1CtxCmqQRPOHJ",  # Drew
                    "name": "Drew", 
                    "reason": "Authoritative male voice",
                    "provider": "elevenlabs"
                }
            ])
        
        # Casual/social content voices
        elif content_type == "casual":
            recommendations.extend([
                {
                    "voice_id": "TX3LPaxmHKxFdv7VOQHJ",  # Liam
                    "name": "Liam",
                    "reason": "Young, energetic voice",
                    "provider": "elevenlabs"
                },
                {
                    "voice_id": "MF3mGyEYCl7XYWbV9V6O",  # Elli
                    "name": "Elli",
                    "reason": "Friendly, approachable voice",
                    "provider": "elevenlabs"
                }
            ])
        
        # Educational content voices
        elif content_type == "educational":
            recommendations.extend([
                {
                    "voice_id": "EXAVITQu4vr4xnSDxMaL",  # Sarah
                    "name": "Sarah",
                    "reason": "Clear, instructional voice",
                    "provider": "elevenlabs"
                },
                {
                    "voice_id": "pNInz6obpgDQGcFmaJgB",  # Adam
                    "name": "Adam",
                    "reason": "Warm, educational tone",
                    "provider": "elevenlabs"
                }
            ])
        
        return recommendations


# Global service instance
_tts_service: Optional[TTSService] = None


def get_tts_service() -> TTSService:
    """Get global TTS service instance"""
    global _tts_service
    if _tts_service is None:
        _tts_service = TTSService()
    return _tts_service


# Provider class aliases for easy imports
TTSProvider = BaseTTSProvider