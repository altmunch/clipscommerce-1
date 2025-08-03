"""
Comprehensive unit tests for AI video generation pipeline including
script generation, provider integrations, video assembly, and UGC testimonials.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock, mock_open
from datetime import datetime, timedelta
import json
import uuid
from pathlib import Path

from app.services.ai.video_generation import VideoGenerationService
from app.services.ai.script_generation import ScriptGenerationService
from app.services.ai.providers import RunwayMLProvider, DIDProvider, HeyGenProvider
from app.services.video_generation.orchestrator import VideoOrchestrator
from app.services.video_generation.script_generation import ScriptGenerator
from app.services.video_generation.text_to_speech import TextToSpeechService
from app.services.video_generation.video_assembly import VideoAssemblyService
from app.services.video_generation.ugc_generation import UGCTestimonialGenerator
from app.services.video_generation.asset_management import AssetManager
from app.models.video_project import (
    VideoProject, VideoSegment, UGCTestimonial, VideoGenerationJob,
    VideoProviderEnum, GenerationStatusEnum, VideoProjectTypeEnum
)
from tests.factories import (
    VideoProjectFactory, VideoSegmentFactory, UGCTestimonialFactory, 
    BrandFactory, ProductFactory
)


class TestVideoGenerationService:
    """Test main video generation service orchestration."""

    @pytest.fixture
    def video_service(self, mock_openai_client, mock_anthropic_client, mock_redis):
        with patch('app.services.ai.video_generation.openai_client', mock_openai_client):
            with patch('app.services.ai.video_generation.anthropic_client', mock_anthropic_client):
                with patch('app.services.ai.video_generation.redis', mock_redis):
                    return VideoGenerationService()

    @pytest.fixture
    def sample_video_project(self, db_session):
        """Create a sample video project for testing."""
        brand = BrandFactory.create()
        product = ProductFactory.create(brand_id=brand.id)
        project = VideoProjectFactory.create(
            brand_id=brand.id,
            product_id=product.id,
            project_type=VideoProjectTypeEnum.PRODUCT_AD
        )
        
        db_session.add_all([brand, product, project])
        db_session.commit()
        return project

    @pytest.mark.unit
    @pytest.mark.ai
    async def test_generate_video_project_success(self, video_service, sample_video_project, db_session):
        """Test successful video project generation."""
        # Mock AI responses
        video_service.openai_client.chat.completions.create.return_value = Mock(
            choices=[Mock(message=Mock(content=json.dumps({
                "script": "Amazing product showcase video script",
                "segments": [
                    {"start": 0, "end": 5, "description": "Product introduction"},
                    {"start": 5, "end": 10, "description": "Feature highlights"}
                ],
                "style": "professional",
                "hooks": ["Discover the future of innovation"]
            })))]
        )
        
        # Mock video provider responses
        with patch('app.services.ai.providers.RunwayMLProvider.generate_video') as mock_runway:
            mock_runway.return_value = {
                "video_url": "https://example.com/generated-video.mp4",
                "job_id": "runway-job-123",
                "status": "completed"
            }
            
            result = await video_service.generate_video_project(sample_video_project.id, db_session)
        
        assert result["status"] == "success"
        assert "video_url" in result
        assert result["project_id"] == str(sample_video_project.id)
        
        # Verify project status updated
        db_session.refresh(sample_video_project)
        assert sample_video_project.status == GenerationStatusEnum.COMPLETED

    @pytest.mark.unit
    @pytest.mark.ai
    async def test_generate_video_with_brand_guidelines(self, video_service, sample_video_project, db_session):
        """Test video generation respects brand guidelines."""
        # Set brand guidelines
        sample_video_project.brand_guidelines = {
            "colors": ["#FF0000", "#00FF00", "#0000FF"],
            "fonts": ["Helvetica", "Arial"],
            "voice": "professional and friendly",
            "logo_url": "https://example.com/logo.png"
        }
        db_session.commit()
        
        video_service.openai_client.chat.completions.create.return_value = Mock(
            choices=[Mock(message=Mock(content=json.dumps({
                "script": "Brand-aligned video script",
                "brand_integration": {
                    "colors_used": ["#FF0000", "#00FF00"],
                    "voice_alignment": "professional and friendly",
                    "logo_placement": "bottom-right"
                }
            })))]
        )
        
        with patch('app.services.ai.providers.RunwayMLProvider.generate_video') as mock_runway:
            mock_runway.return_value = {"video_url": "test.mp4", "job_id": "123"}
            
            result = await video_service.generate_video_project(sample_video_project.id, db_session)
        
        # Verify brand guidelines were passed to AI
        call_args = video_service.openai_client.chat.completions.create.call_args
        prompt = call_args[1]["messages"][0]["content"]
        assert "#FF0000" in prompt
        assert "professional and friendly" in prompt

    @pytest.mark.unit
    async def test_video_generation_error_handling(self, video_service, sample_video_project, db_session):
        """Test error handling during video generation."""
        # Mock AI service failure
        video_service.openai_client.chat.completions.create.side_effect = Exception("AI service unavailable")
        
        result = await video_service.generate_video_project(sample_video_project.id, db_session)
        
        assert result["status"] == "error"
        assert "AI service unavailable" in result["error"]
        
        # Verify project status updated
        db_session.refresh(sample_video_project)
        assert sample_video_project.status == GenerationStatusEnum.FAILED

    @pytest.mark.unit
    async def test_video_cost_calculation(self, video_service, sample_video_project):
        """Test video generation cost calculation."""
        generation_params = {
            "duration": 30,  # seconds
            "quality": "high",
            "provider": "runwayml",
            "segments": 3
        }
        
        estimated_cost = await video_service.calculate_generation_cost(generation_params)
        
        assert estimated_cost > 0
        assert isinstance(estimated_cost, (int, float))

    @pytest.mark.unit
    async def test_progress_tracking(self, video_service, sample_video_project, db_session, mock_redis):
        """Test video generation progress tracking."""
        # Start generation
        await video_service.start_generation_tracking(sample_video_project.id)
        
        # Update progress
        await video_service.update_progress(sample_video_project.id, 50, "Generating segments")
        
        # Verify Redis updates
        mock_redis.set.assert_called()
        
        # Verify database updates
        db_session.refresh(sample_video_project)
        assert sample_video_project.progress_percentage == 50


class TestScriptGenerationService:
    """Test AI-powered script generation."""

    @pytest.fixture
    def script_service(self, mock_openai_client, mock_anthropic_client):
        with patch('app.services.ai.script_generation.openai_client', mock_openai_client):
            with patch('app.services.ai.script_generation.anthropic_client', mock_anthropic_client):
                return ScriptGenerationService()

    @pytest.mark.unit
    @pytest.mark.ai
    async def test_generate_product_script(self, script_service):
        """Test product-focused script generation."""
        product_data = {
            "name": "Amazing Wireless Headphones",
            "description": "Premium noise-canceling wireless headphones",
            "features": ["Noise cancellation", "30-hour battery", "Quick charge"],
            "price": 199.99,
            "target_audience": "Music lovers and professionals"
        }
        
        script_service.openai_client.chat.completions.create.return_value = Mock(
            choices=[Mock(message=Mock(content=json.dumps({
                "script": "Experience crystal-clear audio with our Amazing Wireless Headphones...",
                "hooks": ["Ready to transform your listening experience?"],
                "call_to_action": "Order now and feel the difference!",
                "duration_estimate": 30,
                "segments": [
                    {"timing": "0-5s", "content": "Hook and product introduction"},
                    {"timing": "5-20s", "content": "Feature demonstrations"},
                    {"timing": "20-30s", "content": "Call to action"}
                ]
            })))]
        )
        
        script = await script_service.generate_product_script(product_data)
        
        assert script is not None
        assert "Amazing Wireless Headphones" in script["script"]
        assert len(script["hooks"]) > 0
        assert script["duration_estimate"] > 0
        assert len(script["segments"]) > 0

    @pytest.mark.unit
    @pytest.mark.ai
    async def test_generate_ugc_script(self, script_service):
        """Test UGC testimonial script generation."""
        review_data = {
            "review_text": "This product changed my life! Amazing quality and fast shipping.",
            "rating": 5,
            "reviewer_name": "Sarah M.",
            "product_name": "Life-Changing Widget"
        }
        
        script_service.openai_client.chat.completions.create.return_value = Mock(
            choices=[Mock(message=Mock(content=json.dumps({
                "script": "Hi, I'm Sarah, and I have to tell you about this amazing widget...",
                "emotion": "enthusiastic",
                "authenticity_score": 0.95,
                "key_points": ["Life-changing impact", "Amazing quality", "Fast shipping"]
            })))]
        )
        
        script = await script_service.generate_ugc_script(review_data)
        
        assert script is not None
        assert "Sarah" in script["script"]
        assert script["emotion"] == "enthusiastic"
        assert script["authenticity_score"] > 0.9

    @pytest.mark.unit
    @pytest.mark.ai
    async def test_optimize_for_platform(self, script_service):
        """Test platform-specific script optimization."""
        base_script = {
            "script": "Long detailed product description with many features and benefits...",
            "duration": 60
        }
        
        # Optimize for TikTok (short-form)
        script_service.openai_client.chat.completions.create.return_value = Mock(
            choices=[Mock(message=Mock(content=json.dumps({
                "script": "Quick hook! Amazing product, instant results! 🔥",
                "duration": 15,
                "tiktok_optimizations": ["Trending music integration", "Quick cuts", "Visual effects"]
            })))]
        )
        
        optimized = await script_service.optimize_for_platform(base_script, "tiktok")
        
        assert optimized["duration"] < base_script["duration"]
        assert "tiktok_optimizations" in optimized

    @pytest.mark.unit
    async def test_script_quality_validation(self, script_service):
        """Test script quality validation."""
        high_quality_script = {
            "script": "Compelling hook followed by clear value proposition and strong call to action",
            "hooks": ["Attention-grabbing question"],
            "call_to_action": "Visit our website today",
            "duration_estimate": 30
        }
        
        low_quality_script = {
            "script": "Product good buy now",
            "hooks": [],
            "call_to_action": "",
            "duration_estimate": 5
        }
        
        high_score = await script_service.validate_script_quality(high_quality_script)
        low_score = await script_service.validate_script_quality(low_quality_script)
        
        assert high_score > 0.8
        assert low_score < 0.5

    @pytest.mark.unit
    @pytest.mark.ai
    async def test_a_b_script_generation(self, script_service):
        """Test A/B testing script generation."""
        product_data = {
            "name": "Test Product",
            "description": "Test description"
        }
        
        script_service.openai_client.chat.completions.create.side_effect = [
            Mock(choices=[Mock(message=Mock(content=json.dumps({
                "script": "Version A: Emotional approach with storytelling...",
                "variant": "emotional"
            })))]),
            Mock(choices=[Mock(message=Mock(content=json.dumps({
                "script": "Version B: Logical approach with features...",
                "variant": "logical"
            })))])
        ]
        
        variants = await script_service.generate_ab_scripts(product_data, num_variants=2)
        
        assert len(variants) == 2
        assert variants[0]["variant"] != variants[1]["variant"]


class TestVideoProviders:
    """Test individual video generation provider integrations."""

    @pytest.mark.unit
    async def test_runwayml_provider(self):
        """Test RunwayML provider integration."""
        provider = RunwayMLProvider(api_key="test-key")
        
        mock_response = {
            "id": "runway-job-123",
            "status": "completed",
            "output": ["https://runway.com/output.mp4"],
            "progress": 100
        }
        
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.return_value = Mock(
                status_code=200,
                json=Mock(return_value=mock_response)
            )
            
            result = await provider.generate_video({
                "prompt": "A product showcase video",
                "duration": 10,
                "aspect_ratio": "16:9"
            })
        
        assert result["status"] == "completed"
        assert result["video_url"] == "https://runway.com/output.mp4"
        assert result["job_id"] == "runway-job-123"

    @pytest.mark.unit
    async def test_did_provider_avatar_video(self):
        """Test D-ID provider for avatar-based videos."""
        provider = DIDProvider(api_key="test-key")
        
        mock_response = {
            "id": "did-job-456",
            "status": "done",
            "result_url": "https://did.com/avatar-video.mp4"
        }
        
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.return_value = Mock(
                status_code=201,
                json=Mock(return_value=mock_response)
            )
            
            result = await provider.generate_avatar_video({
                "script": "Hello, this is a testimonial",
                "presenter_id": "amy-jcu3W4UuaKVs6Qb",
                "voice_id": "elevenlabs-voice-123"
            })
        
        assert result["status"] == "completed"
        assert result["video_url"] == "https://did.com/avatar-video.mp4"

    @pytest.mark.unit
    async def test_heygen_provider_ugc_testimonial(self):
        """Test HeyGen provider for UGC testimonials."""
        provider = HeyGenProvider(api_key="test-key")
        
        mock_response = {
            "video_id": "heygen-video-789",
            "status": "completed",
            "video_url": "https://heygen.com/testimonial.mp4",
            "duration": 45.5
        }
        
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.return_value = Mock(
                status_code=200,
                json=Mock(return_value=mock_response)
            )
            
            result = await provider.generate_ugc_testimonial({
                "script": "I love this product because...",
                "avatar_id": "heygen-avatar-casual-female",
                "background": "home_office",
                "emotion": "enthusiastic"
            })
        
        assert result["status"] == "completed"
        assert result["duration"] == 45.5

    @pytest.mark.unit
    async def test_provider_error_handling(self):
        """Test provider error handling and retry logic."""
        provider = RunwayMLProvider(api_key="test-key")
        
        # Test rate limiting
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.return_value = Mock(
                status_code=429,
                json=Mock(return_value={"error": "Rate limit exceeded"})
            )
            
            with pytest.raises(Exception, match="Rate limit"):
                await provider.generate_video({"prompt": "test"})
        
        # Test API error
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.return_value = Mock(
                status_code=500,
                json=Mock(return_value={"error": "Internal server error"})
            )
            
            with pytest.raises(Exception, match="API error"):
                await provider.generate_video({"prompt": "test"})

    @pytest.mark.unit
    async def test_provider_cost_calculation(self):
        """Test cost calculation for different providers."""
        runway = RunwayMLProvider(api_key="test-key")
        did = DIDProvider(api_key="test-key")
        heygen = HeyGenProvider(api_key="test-key")
        
        generation_params = {
            "duration": 30,
            "quality": "high",
            "resolution": "1080p"
        }
        
        runway_cost = await runway.calculate_cost(generation_params)
        did_cost = await did.calculate_cost(generation_params)
        heygen_cost = await heygen.calculate_cost(generation_params)
        
        assert all(cost > 0 for cost in [runway_cost, did_cost, heygen_cost])
        assert isinstance(runway_cost, (int, float))


class TestVideoAssemblyService:
    """Test video assembly and post-processing."""

    @pytest.fixture
    def assembly_service(self):
        return VideoAssemblyService()

    @pytest.fixture
    def mock_video_segments(self):
        return [
            {
                "video_url": "https://example.com/segment1.mp4",
                "start_time": 0,
                "end_time": 10,
                "audio_url": "https://example.com/audio1.mp3"
            },
            {
                "video_url": "https://example.com/segment2.mp4", 
                "start_time": 10,
                "end_time": 20,
                "audio_url": "https://example.com/audio2.mp3"
            }
        ]

    @pytest.mark.unit
    async def test_assemble_video_segments(self, assembly_service, mock_video_segments):
        """Test assembling multiple video segments."""
        with patch('subprocess.run') as mock_subprocess:
            mock_subprocess.return_value = Mock(returncode=0)
            
            with patch('builtins.open', mock_open()):
                result = await assembly_service.assemble_segments(
                    mock_video_segments,
                    output_path="/tmp/assembled_video.mp4"
                )
        
        assert result["success"] is True
        assert result["output_path"] == "/tmp/assembled_video.mp4"
        
        # Verify FFmpeg was called
        mock_subprocess.assert_called()
        ffmpeg_args = mock_subprocess.call_args[0][0]
        assert "ffmpeg" in ffmpeg_args[0]

    @pytest.mark.unit
    async def test_add_background_music(self, assembly_service):
        """Test adding background music to video."""
        with patch('subprocess.run') as mock_subprocess:
            mock_subprocess.return_value = Mock(returncode=0)
            
            result = await assembly_service.add_background_music(
                video_path="/tmp/video.mp4",
                music_path="/tmp/music.mp3",
                volume=0.3
            )
        
        assert result["success"] is True
        
        # Check FFmpeg command includes music mixing
        ffmpeg_args = mock_subprocess.call_args[0][0]
        assert "-filter_complex" in ffmpeg_args

    @pytest.mark.unit
    async def test_add_text_overlays(self, assembly_service):
        """Test adding text overlays to video."""
        overlays = [
            {
                "text": "Amazing Product!",
                "start_time": 2,
                "end_time": 5,
                "position": "center",
                "font_size": 48,
                "color": "white"
            }
        ]
        
        with patch('subprocess.run') as mock_subprocess:
            mock_subprocess.return_value = Mock(returncode=0)
            
            result = await assembly_service.add_text_overlays(
                video_path="/tmp/video.mp4",
                overlays=overlays
            )
        
        assert result["success"] is True

    @pytest.mark.unit
    async def test_apply_brand_elements(self, assembly_service):
        """Test applying brand elements (logo, colors) to video."""
        brand_elements = {
            "logo_url": "https://example.com/logo.png",
            "logo_position": "bottom-right",
            "logo_opacity": 0.8,
            "brand_colors": ["#FF0000", "#00FF00"],
            "color_overlay": {"color": "#FF0000", "opacity": 0.1}
        }
        
        with patch('subprocess.run') as mock_subprocess:
            mock_subprocess.return_value = Mock(returncode=0)
            
            with patch('httpx.AsyncClient.get') as mock_get:
                mock_get.return_value = Mock(content=b"fake_logo_data")
                
                result = await assembly_service.apply_brand_elements(
                    video_path="/tmp/video.mp4",
                    brand_elements=brand_elements
                )
        
        assert result["success"] is True

    @pytest.mark.unit
    async def test_optimize_for_platform(self, assembly_service):
        """Test platform-specific video optimization."""
        # TikTok optimization (vertical, specific specs)
        with patch('subprocess.run') as mock_subprocess:
            mock_subprocess.return_value = Mock(returncode=0)
            
            result = await assembly_service.optimize_for_platform(
                video_path="/tmp/video.mp4",
                platform="tiktok"
            )
        
        assert result["success"] is True
        
        # Check FFmpeg includes aspect ratio conversion
        ffmpeg_args = mock_subprocess.call_args[0][0]
        assert "-aspect" in ffmpeg_args or "-vf" in ffmpeg_args

    @pytest.mark.unit
    async def test_ffmpeg_error_handling(self, assembly_service):
        """Test FFmpeg error handling."""
        with patch('subprocess.run') as mock_subprocess:
            mock_subprocess.return_value = Mock(
                returncode=1,
                stderr="FFmpeg error: invalid input"
            )
            
            result = await assembly_service.assemble_segments(
                [{"video_url": "invalid.mp4"}],
                output_path="/tmp/output.mp4"
            )
        
        assert result["success"] is False
        assert "FFmpeg error" in result["error"]


class TestTextToSpeechService:
    """Test text-to-speech generation."""

    @pytest.fixture
    def tts_service(self):
        return TextToSpeechService()

    @pytest.mark.unit
    async def test_elevenlabs_voice_generation(self, tts_service):
        """Test ElevenLabs voice generation."""
        mock_response = Mock()
        mock_response.content = b"fake_audio_data"
        mock_response.status_code = 200
        
        with patch('httpx.AsyncClient.post', return_value=mock_response):
            result = await tts_service.generate_speech(
                text="Hello, this is a test voice generation",
                voice_id="elevenlabs-voice-123",
                provider="elevenlabs"
            )
        
        assert result["success"] is True
        assert result["audio_data"] == b"fake_audio_data"

    @pytest.mark.unit
    async def test_openai_voice_generation(self, tts_service):
        """Test OpenAI TTS voice generation."""
        mock_response = Mock()
        mock_response.content = b"openai_audio_data"
        mock_response.status_code = 200
        
        with patch('httpx.AsyncClient.post', return_value=mock_response):
            result = await tts_service.generate_speech(
                text="OpenAI voice generation test",
                voice="alloy",
                provider="openai"
            )
        
        assert result["success"] is True
        assert result["audio_data"] == b"openai_audio_data"

    @pytest.mark.unit
    async def test_voice_cloning(self, tts_service):
        """Test voice cloning functionality."""
        with patch('httpx.AsyncClient.post') as mock_post:
            # Mock voice cloning training
            mock_post.return_value = Mock(
                status_code=200,
                json=Mock(return_value={"voice_id": "cloned-voice-456"})
            )
            
            result = await tts_service.clone_voice(
                sample_audio_url="https://example.com/voice_sample.mp3",
                voice_name="Custom Brand Voice"
            )
        
        assert result["voice_id"] == "cloned-voice-456"

    @pytest.mark.unit
    async def test_speech_timing_analysis(self, tts_service):
        """Test speech timing and pacing analysis."""
        script = "This is a test script with multiple sentences. Each sentence should be timed properly."
        
        timing_analysis = await tts_service.analyze_speech_timing(script)
        
        assert timing_analysis["estimated_duration"] > 0
        assert timing_analysis["word_count"] > 0
        assert len(timing_analysis["sentence_timings"]) > 0


class TestUGCTestimonialGenerator:
    """Test UGC testimonial generation."""

    @pytest.fixture
    def ugc_generator(self, mock_openai_client):
        with patch('app.services.video_generation.ugc_generation.openai_client', mock_openai_client):
            return UGCTestimonialGenerator()

    @pytest.fixture
    def sample_reviews(self):
        return [
            {
                "text": "This product is amazing! Changed my daily routine completely.",
                "rating": 5,
                "reviewer": "Sarah M.",
                "verified_purchase": True
            },
            {
                "text": "Good quality, fast shipping. Exactly as described.",
                "rating": 4,
                "reviewer": "Mike T.", 
                "verified_purchase": True
            }
        ]

    @pytest.mark.unit
    @pytest.mark.ai
    async def test_generate_authentic_testimonial(self, ugc_generator, sample_reviews):
        """Test generating authentic-sounding testimonials."""
        ugc_generator.openai_client.chat.completions.create.return_value = Mock(
            choices=[Mock(message=Mock(content=json.dumps({
                "script": "Hi everyone! I had to share my experience with this product...",
                "avatar_style": "casual_female_25_35",
                "background": "home_office",
                "emotion": "enthusiastic",
                "authenticity_score": 0.92,
                "key_talking_points": ["life-changing", "daily routine", "highly recommend"]
            })))]
        )
        
        testimonial = await ugc_generator.generate_testimonial_from_review(sample_reviews[0])
        
        assert testimonial["script"] is not None
        assert testimonial["authenticity_score"] > 0.9
        assert "casual_female" in testimonial["avatar_style"]

    @pytest.mark.unit
    async def test_diversify_testimonial_avatars(self, ugc_generator, sample_reviews):
        """Test avatar diversity in testimonials."""
        testimonials = []
        
        for i, review in enumerate(sample_reviews):
            ugc_generator.openai_client.chat.completions.create.return_value = Mock(
                choices=[Mock(message=Mock(content=json.dumps({
                    "avatar_style": f"diverse_avatar_{i}",
                    "script": f"Testimonial script {i}",
                    "demographics": {
                        "age_range": "25-35" if i == 0 else "35-45",
                        "gender": "female" if i == 0 else "male",
                        "ethnicity": "caucasian" if i == 0 else "hispanic"
                    }
                })))]
            )
            
            testimonial = await ugc_generator.generate_testimonial_from_review(review)
            testimonials.append(testimonial)
        
        # Verify diversity
        assert testimonials[0]["demographics"]["gender"] != testimonials[1]["demographics"]["gender"]
        assert testimonials[0]["demographics"]["age_range"] != testimonials[1]["demographics"]["age_range"]

    @pytest.mark.unit
    async def test_testimonial_quality_filtering(self, ugc_generator):
        """Test filtering low-quality testimonials."""
        low_quality_review = {
            "text": "ok",  # Too short
            "rating": 2,  # Low rating
            "reviewer": "Anonymous",
            "verified_purchase": False
        }
        
        high_quality_review = {
            "text": "Excellent product with outstanding customer service and fast delivery",
            "rating": 5,
            "reviewer": "John D.",
            "verified_purchase": True
        }
        
        low_score = await ugc_generator.assess_review_quality(low_quality_review)
        high_score = await ugc_generator.assess_review_quality(high_quality_review)
        
        assert low_score < 0.5
        assert high_score > 0.8

    @pytest.mark.unit
    async def test_batch_testimonial_generation(self, ugc_generator, sample_reviews):
        """Test generating multiple testimonials in batch."""
        ugc_generator.openai_client.chat.completions.create.side_effect = [
            Mock(choices=[Mock(message=Mock(content=json.dumps({
                "script": f"Testimonial script {i}",
                "avatar_style": f"avatar_{i}"
            })))]) for i in range(len(sample_reviews))
        ]
        
        testimonials = await ugc_generator.generate_batch_testimonials(sample_reviews)
        
        assert len(testimonials) == len(sample_reviews)
        assert all("script" in t for t in testimonials)


class TestAssetManager:
    """Test video asset management."""

    @pytest.fixture
    def asset_manager(self, mock_file_storage):
        with patch('app.services.video_generation.asset_management.file_storage', mock_file_storage):
            return AssetManager()

    @pytest.mark.unit
    async def test_download_and_cache_asset(self, asset_manager, mock_file_storage):
        """Test downloading and caching video assets."""
        asset_url = "https://example.com/product-image.jpg"
        
        # Mock HTTP download
        mock_response = Mock()
        mock_response.content = b"fake_image_data"
        mock_response.status_code = 200
        
        with patch('httpx.AsyncClient.get', return_value=mock_response):
            result = await asset_manager.download_asset(asset_url)
        
        assert result["success"] is True
        assert result["local_path"] is not None
        mock_file_storage.upload.assert_called()

    @pytest.mark.unit
    async def test_process_brand_assets(self, asset_manager):
        """Test processing brand assets for video use."""
        brand_assets = {
            "logo_url": "https://example.com/logo.png",
            "color_palette": ["#FF0000", "#00FF00", "#0000FF"],
            "fonts": ["Arial", "Helvetica"]
        }
        
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_get.return_value = Mock(content=b"logo_data", status_code=200)
            
            processed = await asset_manager.process_brand_assets(brand_assets)
        
        assert processed["logo_path"] is not None
        assert len(processed["color_palette"]) == 3

    @pytest.mark.unit
    async def test_generate_thumbnails(self, asset_manager):
        """Test video thumbnail generation."""
        video_path = "/tmp/test_video.mp4"
        
        with patch('subprocess.run') as mock_subprocess:
            mock_subprocess.return_value = Mock(returncode=0)
            
            thumbnails = await asset_manager.generate_thumbnails(
                video_path, 
                timestamps=[5, 15, 25]
            )
        
        assert len(thumbnails) == 3
        assert all(thumb.endswith('.jpg') for thumb in thumbnails)

    @pytest.mark.unit
    async def test_asset_optimization(self, asset_manager):
        """Test asset optimization for different platforms."""
        asset_path = "/tmp/image.jpg"
        
        with patch('PIL.Image.open') as mock_pil:
            mock_image = Mock()
            mock_image.resize = Mock(return_value=mock_image)
            mock_image.save = Mock()
            mock_pil.return_value = mock_image
            
            optimized = await asset_manager.optimize_for_platform(
                asset_path,
                platform="tiktok"
            )
        
        assert optimized["success"] is True
        mock_image.resize.assert_called()  # Image was resized

    @pytest.mark.unit
    async def test_cleanup_temp_assets(self, asset_manager):
        """Test cleanup of temporary assets."""
        temp_files = ["/tmp/temp1.jpg", "/tmp/temp2.mp4", "/tmp/temp3.png"]
        
        with patch('os.path.exists', return_value=True):
            with patch('os.remove') as mock_remove:
                await asset_manager.cleanup_temp_assets(temp_files)
        
        assert mock_remove.call_count == len(temp_files)


class TestVideoOrchestrator:
    """Test video generation orchestration."""

    @pytest.fixture
    def orchestrator(self, mock_redis, mock_celery):
        with patch('app.services.video_generation.orchestrator.redis', mock_redis):
            with patch('app.services.video_generation.orchestrator.celery', mock_celery):
                return VideoOrchestrator()

    @pytest.mark.unit
    async def test_orchestrate_full_pipeline(self, orchestrator, sample_video_project, db_session):
        """Test orchestrating the full video generation pipeline."""
        # Mock all service calls
        with patch.object(orchestrator, 'generate_script') as mock_script:
            with patch.object(orchestrator, 'generate_video_segments') as mock_segments:
                with patch.object(orchestrator, 'assemble_final_video') as mock_assemble:
                    
                    mock_script.return_value = {"script": "test script", "segments": []}
                    mock_segments.return_value = [{"video_url": "segment1.mp4"}]
                    mock_assemble.return_value = {"video_url": "final.mp4"}
                    
                    result = await orchestrator.generate_complete_video(sample_video_project.id, db_session)
        
        assert result["status"] == "success"
        assert result["video_url"] == "final.mp4"

    @pytest.mark.unit
    async def test_pipeline_error_recovery(self, orchestrator, sample_video_project, db_session):
        """Test error recovery in the pipeline."""
        # Mock script generation failure
        with patch.object(orchestrator, 'generate_script', side_effect=Exception("Script generation failed")):
            result = await orchestrator.generate_complete_video(sample_video_project.id, db_session)
        
        assert result["status"] == "error"
        assert "Script generation failed" in result["error"]

    @pytest.mark.unit
    async def test_parallel_segment_generation(self, orchestrator):
        """Test parallel generation of video segments."""
        segments = [
            {"prompt": "Product intro", "duration": 5},
            {"prompt": "Feature demo", "duration": 10}, 
            {"prompt": "Call to action", "duration": 5}
        ]
        
        with patch.object(orchestrator, 'generate_single_segment') as mock_generate:
            mock_generate.side_effect = [
                {"video_url": f"segment{i}.mp4", "duration": seg["duration"]}
                for i, seg in enumerate(segments)
            ]
            
            results = await orchestrator.generate_segments_parallel(segments)
        
        assert len(results) == 3
        assert all(r["video_url"] for r in results)

    @pytest.mark.unit
    async def test_quality_control_checks(self, orchestrator):
        """Test quality control checks throughout pipeline."""
        video_data = {
            "video_url": "https://example.com/video.mp4",
            "duration": 30,
            "resolution": "1920x1080",
            "audio_quality": "high"
        }
        
        quality_score = await orchestrator.assess_video_quality(video_data)
        
        assert 0 <= quality_score <= 1
        assert isinstance(quality_score, float)