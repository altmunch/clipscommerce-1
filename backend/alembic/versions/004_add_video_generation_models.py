"""Add video generation models

Revision ID: 004_add_video_generation_models
Revises: 003_add_tiktok_trend_tables
Create Date: 2025-01-21 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '004_add_video_generation_models'
down_revision = '003_add_tiktok_trend_tables'
branch_labels = None
depends_on = None


def upgrade():
    """Create video generation tables"""
    
    # Create video_projects table
    op.create_table(
        'video_projects',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('project_type', sa.Enum(
            'PRODUCT_AD', 'UGC_TESTIMONIAL', 'BRAND_STORY', 'TUTORIAL', 'SOCIAL_POST',
            name='videoprojecttypeenum'
        ), nullable=False),
        
        # Associated entities
        sa.Column('brand_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('campaign_id', postgresql.UUID(as_uuid=True), nullable=True),
        
        # Project configuration
        sa.Column('target_platform', sa.String(50)),
        sa.Column('target_duration', sa.Float()),
        sa.Column('aspect_ratio', sa.String(20), default='9:16'),
        sa.Column('quality', sa.Enum(
            'LOW', 'MEDIUM', 'HIGH', 'ULTRA',
            name='videoqualityenum'
        ), default='MEDIUM'),
        sa.Column('style', sa.Enum(
            'REALISTIC', 'ANIMATED', 'CARTOON', 'CINEMATIC', 'PROFESSIONAL', 'CASUAL', 'TESTIMONIAL',
            name='videostyleenum'
        ), default='PROFESSIONAL'),
        
        # Generation settings
        sa.Column('preferred_provider', sa.Enum(
            'RUNWAYML', 'DID', 'HEYGEN', 'SYNTHESIA', 'REPLICATE', 'INVIDEO', 'STABLE_VIDEO',
            name='videoproviderenum'
        )),
        sa.Column('voice_id', sa.String(100)),
        sa.Column('language', sa.String(10), default='en'),
        
        # Status and progress
        sa.Column('status', sa.Enum(
            'PENDING', 'IN_PROGRESS', 'COMPLETED', 'FAILED', 'CANCELLED',
            name='generationstatusenum'
        ), default='PENDING'),
        sa.Column('progress_percentage', sa.Float(), default=0.0),
        
        # Costs and timing
        sa.Column('estimated_cost', sa.Float(), default=0.0),
        sa.Column('actual_cost', sa.Float(), default=0.0),
        sa.Column('estimated_completion_time', sa.DateTime()),
        sa.Column('generation_started_at', sa.DateTime()),
        sa.Column('generation_completed_at', sa.DateTime()),
        
        # Results
        sa.Column('final_video_url', sa.String(500)),
        sa.Column('preview_video_url', sa.String(500)),
        sa.Column('thumbnail_url', sa.String(500)),
        
        # JSON fields
        sa.Column('brand_guidelines', postgresql.JSONB()),
        sa.Column('generation_config', postgresql.JSONB()),
        sa.Column('editing_timeline', postgresql.JSONB()),
        sa.Column('metrics', postgresql.JSONB()),
        
        # Audit fields
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('created_by', postgresql.UUID(as_uuid=True)),
        
        # Foreign key constraints
        sa.ForeignKeyConstraint(['brand_id'], ['brands.id']),
        sa.ForeignKeyConstraint(['product_id'], ['products.id']),
        sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id']),
    )
    
    # Create video_segments table
    op.create_table(
        'video_segments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
        
        # Segment metadata
        sa.Column('segment_number', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(255)),
        
        # Timing
        sa.Column('start_time', sa.Float(), nullable=False),
        sa.Column('end_time', sa.Float(), nullable=False),
        sa.Column('duration', sa.Float(), nullable=False),
        
        # Generation parameters
        sa.Column('prompt', sa.Text(), nullable=False),
        sa.Column('enhanced_prompt', sa.Text()),
        sa.Column('style', sa.Enum(
            'REALISTIC', 'ANIMATED', 'CARTOON', 'CINEMATIC', 'PROFESSIONAL', 'CASUAL', 'TESTIMONIAL',
            name='videostyleenum'
        )),
        sa.Column('quality', sa.Enum(
            'LOW', 'MEDIUM', 'HIGH', 'ULTRA',
            name='videoqualityenum'
        )),
        sa.Column('provider', sa.Enum(
            'RUNWAYML', 'DID', 'HEYGEN', 'SYNTHESIA', 'REPLICATE', 'INVIDEO', 'STABLE_VIDEO',
            name='videoproviderenum'
        )),
        
        # Provider-specific data
        sa.Column('provider_job_id', sa.String(200)),
        sa.Column('provider_response', postgresql.JSONB()),
        
        # Status and results
        sa.Column('status', sa.Enum(
            'PENDING', 'IN_PROGRESS', 'COMPLETED', 'FAILED', 'CANCELLED',
            name='generationstatusenum'
        ), default='PENDING'),
        sa.Column('video_url', sa.String(500)),
        sa.Column('preview_url', sa.String(500)),
        sa.Column('thumbnail_url', sa.String(500)),
        
        # Generation metadata
        sa.Column('generation_time', sa.Float()),
        sa.Column('cost', sa.Float(), default=0.0),
        sa.Column('retry_count', sa.Integer(), default=0),
        sa.Column('error_message', sa.Text()),
        
        # Audio/speech
        sa.Column('has_speech', sa.Boolean(), default=False),
        sa.Column('speech_text', sa.Text()),
        sa.Column('speech_url', sa.String(500)),
        
        # Technical metadata
        sa.Column('resolution', sa.String(20)),
        sa.Column('fps', sa.Integer()),
        sa.Column('file_size', sa.Integer()),
        sa.Column('format', sa.String(10)),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('generated_at', sa.DateTime()),
        
        # Foreign key constraints
        sa.ForeignKeyConstraint(['project_id'], ['video_projects.id'], ondelete='CASCADE'),
    )
    
    # Create broll_clips table
    op.create_table(
        'broll_clips',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
        
        # Clip metadata
        sa.Column('title', sa.String(255)),
        sa.Column('description', sa.Text()),
        sa.Column('duration', sa.Float(), nullable=False),
        sa.Column('tags', postgresql.JSONB()),
        
        # Source information
        sa.Column('source', sa.String(50)),
        sa.Column('source_provider', sa.String(50)),
        sa.Column('source_id', sa.String(200)),
        sa.Column('license_type', sa.String(50)),
        
        # URLs and files
        sa.Column('video_url', sa.String(500), nullable=False),
        sa.Column('thumbnail_url', sa.String(500)),
        sa.Column('local_path', sa.String(500)),
        
        # Usage in project
        sa.Column('used_in_timeline', sa.Boolean(), default=False),
        sa.Column('timeline_start_time', sa.Float()),
        sa.Column('timeline_end_time', sa.Float()),
        sa.Column('overlay_position', sa.String(50)),
        sa.Column('opacity', sa.Float(), default=1.0),
        
        # Technical specs
        sa.Column('resolution', sa.String(20)),
        sa.Column('fps', sa.Integer()),
        sa.Column('file_size', sa.Integer()),
        sa.Column('format', sa.String(10)),
        
        # Cost and licensing
        sa.Column('cost', sa.Float(), default=0.0),
        sa.Column('license_expires_at', sa.DateTime()),
        sa.Column('attribution_required', sa.Boolean(), default=False),
        sa.Column('attribution_text', sa.Text()),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        
        # Foreign key constraints
        sa.ForeignKeyConstraint(['project_id'], ['video_projects.id'], ondelete='CASCADE'),
    )
    
    # Create video_assets table
    op.create_table(
        'video_assets',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
        
        # Asset metadata
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('asset_type', sa.String(50)),
        sa.Column('category', sa.String(50)),
        
        # File information
        sa.Column('file_url', sa.String(500), nullable=False),
        sa.Column('local_path', sa.String(500)),
        sa.Column('file_size', sa.Integer()),
        sa.Column('mime_type', sa.String(100)),
        
        # Usage in project
        sa.Column('usage_context', sa.String(100)),
        sa.Column('position', sa.String(50)),
        sa.Column('scale', sa.Float(), default=1.0),
        sa.Column('opacity', sa.Float(), default=1.0),
        sa.Column('start_time', sa.Float()),
        sa.Column('end_time', sa.Float()),
        
        # Processing settings
        sa.Column('processed', sa.Boolean(), default=False),
        sa.Column('processed_url', sa.String(500)),
        sa.Column('processing_settings', postgresql.JSONB()),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        
        # Foreign key constraints
        sa.ForeignKeyConstraint(['project_id'], ['video_projects.id'], ondelete='CASCADE'),
    )
    
    # Create ugc_testimonials table
    op.create_table(
        'ugc_testimonials',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
        
        # Source review/testimonial
        sa.Column('original_review_text', sa.Text(), nullable=False),
        sa.Column('review_source', sa.String(100)),
        sa.Column('review_rating', sa.Float()),
        sa.Column('review_author', sa.String(200)),
        
        # Avatar configuration
        sa.Column('avatar_provider', sa.String(50)),
        sa.Column('avatar_id', sa.String(200)),
        sa.Column('avatar_gender', sa.String(20)),
        sa.Column('avatar_ethnicity', sa.String(50)),
        sa.Column('avatar_age_range', sa.String(20)),
        
        # Generated script
        sa.Column('generated_script', sa.Text()),
        sa.Column('script_emotion', sa.String(50)),
        sa.Column('script_language', sa.String(10), default='en'),
        
        # Voice settings
        sa.Column('voice_provider', sa.String(50)),
        sa.Column('voice_id', sa.String(200)),
        sa.Column('voice_settings', postgresql.JSONB()),
        
        # Generation results
        sa.Column('status', sa.Enum(
            'PENDING', 'IN_PROGRESS', 'COMPLETED', 'FAILED', 'CANCELLED',
            name='generationstatusenum'
        ), default='PENDING'),
        sa.Column('video_url', sa.String(500)),
        sa.Column('audio_url', sa.String(500)),
        sa.Column('duration', sa.Float()),
        
        # Cost and metadata
        sa.Column('generation_cost', sa.Float(), default=0.0),
        sa.Column('generation_time', sa.Float()),
        sa.Column('provider_job_id', sa.String(200)),
        sa.Column('error_message', sa.Text()),
        
        # Usage tracking
        sa.Column('used_in_campaigns', postgresql.JSONB()),
        sa.Column('performance_metrics', postgresql.JSONB()),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('generated_at', sa.DateTime()),
        
        # Foreign key constraints
        sa.ForeignKeyConstraint(['project_id'], ['video_projects.id'], ondelete='CASCADE'),
    )
    
    # Create video_generation_jobs table
    op.create_table(
        'video_generation_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
        
        # Job metadata
        sa.Column('job_type', sa.String(50)),
        sa.Column('celery_task_id', sa.String(200)),
        
        # Job parameters
        sa.Column('job_config', postgresql.JSONB()),
        sa.Column('priority', sa.Integer(), default=0),
        
        # Status and progress
        sa.Column('status', sa.Enum(
            'PENDING', 'IN_PROGRESS', 'COMPLETED', 'FAILED', 'CANCELLED',
            name='generationstatusenum'
        ), default='PENDING'),
        sa.Column('progress_percentage', sa.Float(), default=0.0),
        sa.Column('current_step', sa.String(200)),
        
        # Results and errors
        sa.Column('result', postgresql.JSONB()),
        sa.Column('error_message', sa.Text()),
        sa.Column('retry_count', sa.Integer(), default=0),
        sa.Column('max_retries', sa.Integer(), default=3),
        
        # Timing
        sa.Column('started_at', sa.DateTime()),
        sa.Column('completed_at', sa.DateTime()),
        sa.Column('estimated_completion', sa.DateTime()),
        
        # Resource usage
        sa.Column('processing_time', sa.Float()),
        sa.Column('cost', sa.Float(), default=0.0),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        
        # Foreign key constraints
        sa.ForeignKeyConstraint(['project_id'], ['video_projects.id'], ondelete='CASCADE'),
    )
    
    # Create indexes for better performance
    op.create_index('idx_video_projects_status', 'video_projects', ['status'])
    op.create_index('idx_video_projects_created_at', 'video_projects', ['created_at'])
    op.create_index('idx_video_projects_brand_id', 'video_projects', ['brand_id'])
    op.create_index('idx_video_projects_product_id', 'video_projects', ['product_id'])
    
    op.create_index('idx_video_segments_project_id', 'video_segments', ['project_id'])
    op.create_index('idx_video_segments_status', 'video_segments', ['status'])
    op.create_index('idx_video_segments_provider', 'video_segments', ['provider'])
    
    op.create_index('idx_broll_clips_project_id', 'broll_clips', ['project_id'])
    op.create_index('idx_broll_clips_source', 'broll_clips', ['source'])
    
    op.create_index('idx_video_assets_project_id', 'video_assets', ['project_id'])
    op.create_index('idx_video_assets_type', 'video_assets', ['asset_type'])
    
    op.create_index('idx_ugc_testimonials_project_id', 'ugc_testimonials', ['project_id'])
    op.create_index('idx_ugc_testimonials_status', 'ugc_testimonials', ['status'])
    op.create_index('idx_ugc_testimonials_provider', 'ugc_testimonials', ['avatar_provider'])
    
    op.create_index('idx_video_generation_jobs_project_id', 'video_generation_jobs', ['project_id'])
    op.create_index('idx_video_generation_jobs_status', 'video_generation_jobs', ['status'])
    op.create_index('idx_video_generation_jobs_celery_task_id', 'video_generation_jobs', ['celery_task_id'])


def downgrade():
    """Drop video generation tables"""
    
    # Drop indexes first
    op.drop_index('idx_video_generation_jobs_celery_task_id')
    op.drop_index('idx_video_generation_jobs_status')
    op.drop_index('idx_video_generation_jobs_project_id')
    
    op.drop_index('idx_ugc_testimonials_provider')
    op.drop_index('idx_ugc_testimonials_status')
    op.drop_index('idx_ugc_testimonials_project_id')
    
    op.drop_index('idx_video_assets_type')
    op.drop_index('idx_video_assets_project_id')
    
    op.drop_index('idx_broll_clips_source')
    op.drop_index('idx_broll_clips_project_id')
    
    op.drop_index('idx_video_segments_provider')
    op.drop_index('idx_video_segments_status')
    op.drop_index('idx_video_segments_project_id')
    
    op.drop_index('idx_video_projects_product_id')
    op.drop_index('idx_video_projects_brand_id')
    op.drop_index('idx_video_projects_created_at')
    op.drop_index('idx_video_projects_status')
    
    # Drop tables in reverse dependency order
    op.drop_table('video_generation_jobs')
    op.drop_table('ugc_testimonials')
    op.drop_table('video_assets')
    op.drop_table('broll_clips')
    op.drop_table('video_segments')
    op.drop_table('video_projects')
    
    # Drop enum types
    op.execute("DROP TYPE IF EXISTS generationstatusenum")
    op.execute("DROP TYPE IF EXISTS videoproviderenum")
    op.execute("DROP TYPE IF EXISTS videostyleenum")
    op.execute("DROP TYPE IF EXISTS videoqualityenum")
    op.execute("DROP TYPE IF EXISTS videoprojecttypeenum")