"""Add TikTok trend tables

Revision ID: 003
Revises: 002
Create Date: 2024-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade():
    # Create tiktok_trends table
    op.create_table(
        'tiktok_trends',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('trend_id', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=500), nullable=False),
        sa.Column('normalized_name', sa.String(length=500), nullable=True),
        sa.Column('trend_type', sa.String(length=50), nullable=False),
        sa.Column('trend_status', sa.String(length=50), nullable=False),
        sa.Column('content_category', sa.String(length=50), nullable=True),
        sa.Column('total_videos', sa.BigInteger(), nullable=True),
        sa.Column('total_views', sa.BigInteger(), nullable=True),
        sa.Column('total_likes', sa.BigInteger(), nullable=True),
        sa.Column('total_shares', sa.BigInteger(), nullable=True),
        sa.Column('total_comments', sa.BigInteger(), nullable=True),
        sa.Column('viral_score', sa.Float(), nullable=True),
        sa.Column('growth_rate', sa.Float(), nullable=True),
        sa.Column('engagement_rate', sa.Float(), nullable=True),
        sa.Column('velocity', sa.Float(), nullable=True),
        sa.Column('first_detected', sa.DateTime(), nullable=False),
        sa.Column('peak_time', sa.DateTime(), nullable=True),
        sa.Column('predicted_end', sa.DateTime(), nullable=True),
        sa.Column('last_scraped', sa.DateTime(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('keywords', sa.JSON(), nullable=True),
        sa.Column('hashtags', sa.JSON(), nullable=True),
        sa.Column('geographic_data', sa.JSON(), nullable=True),
        sa.Column('demographic_data', sa.JSON(), nullable=True),
        sa.Column('tiktok_metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for tiktok_trends
    op.create_index('idx_tiktok_trend_status_score', 'tiktok_trends', ['trend_status', 'viral_score'])
    op.create_index('idx_tiktok_trend_type_category', 'tiktok_trends', ['trend_type', 'content_category'])
    op.create_index('idx_tiktok_trend_detected_score', 'tiktok_trends', ['first_detected', 'viral_score'])
    op.create_index('idx_tiktok_trend_active', 'tiktok_trends', ['is_active', 'viral_score'])
    op.create_index(op.f('ix_tiktok_trends_name'), 'tiktok_trends', ['name'])
    op.create_index(op.f('ix_tiktok_trends_trend_id'), 'tiktok_trends', ['trend_id'], unique=True)
    op.create_index(op.f('ix_tiktok_trends_trend_status'), 'tiktok_trends', ['trend_status'])
    op.create_index(op.f('ix_tiktok_trends_trend_type'), 'tiktok_trends', ['trend_type'])
    op.create_index(op.f('ix_tiktok_trends_normalized_name'), 'tiktok_trends', ['normalized_name'])
    op.create_index(op.f('ix_tiktok_trends_content_category'), 'tiktok_trends', ['content_category'])
    op.create_index(op.f('ix_tiktok_trends_viral_score'), 'tiktok_trends', ['viral_score'])

    # Create tiktok_videos table
    op.create_table(
        'tiktok_videos',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('video_id', sa.String(length=100), nullable=False),
        sa.Column('trend_id', sa.Integer(), nullable=True),
        sa.Column('title', sa.Text(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('duration', sa.Integer(), nullable=True),
        sa.Column('creator_username', sa.String(length=100), nullable=True),
        sa.Column('creator_display_name', sa.String(length=200), nullable=True),
        sa.Column('creator_follower_count', sa.Integer(), nullable=True),
        sa.Column('creator_verified', sa.Boolean(), nullable=True),
        sa.Column('view_count', sa.BigInteger(), nullable=True),
        sa.Column('like_count', sa.Integer(), nullable=True),
        sa.Column('share_count', sa.Integer(), nullable=True),
        sa.Column('comment_count', sa.Integer(), nullable=True),
        sa.Column('engagement_rate', sa.Float(), nullable=True),
        sa.Column('hashtags', sa.JSON(), nullable=True),
        sa.Column('mentions', sa.JSON(), nullable=True),
        sa.Column('sounds_used', sa.JSON(), nullable=True),
        sa.Column('effects_used', sa.JSON(), nullable=True),
        sa.Column('transcript', sa.Text(), nullable=True),
        sa.Column('visual_elements', sa.JSON(), nullable=True),
        sa.Column('content_hooks', sa.JSON(), nullable=True),
        sa.Column('video_structure', sa.JSON(), nullable=True),
        sa.Column('tiktok_url', sa.String(length=500), nullable=True),
        sa.Column('posted_at', sa.DateTime(), nullable=True),
        sa.Column('video_quality', sa.String(length=20), nullable=True),
        sa.Column('scraped_at', sa.DateTime(), nullable=True),
        sa.Column('scraping_source', sa.String(length=100), nullable=True),
        sa.Column('raw_data', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['trend_id'], ['tiktok_trends.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for tiktok_videos
    op.create_index('idx_tiktok_video_creator', 'tiktok_videos', ['creator_username'])
    op.create_index('idx_tiktok_video_engagement', 'tiktok_videos', ['view_count', 'like_count'])
    op.create_index('idx_tiktok_video_posted', 'tiktok_videos', ['posted_at'])
    op.create_index('idx_tiktok_video_scraped', 'tiktok_videos', ['scraped_at'])
    op.create_index(op.f('ix_tiktok_videos_video_id'), 'tiktok_videos', ['video_id'], unique=True)
    op.create_index(op.f('ix_tiktok_videos_trend_id'), 'tiktok_videos', ['trend_id'])

    # Create tiktok_hashtags table
    op.create_table(
        'tiktok_hashtags',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('hashtag', sa.String(length=200), nullable=False),
        sa.Column('normalized_hashtag', sa.String(length=200), nullable=True),
        sa.Column('trend_id', sa.Integer(), nullable=True),
        sa.Column('total_videos', sa.BigInteger(), nullable=True),
        sa.Column('total_views', sa.BigInteger(), nullable=True),
        sa.Column('usage_velocity', sa.Float(), nullable=True),
        sa.Column('is_trending', sa.Boolean(), nullable=True),
        sa.Column('trend_score', sa.Float(), nullable=True),
        sa.Column('first_seen', sa.DateTime(), nullable=True),
        sa.Column('peak_usage', sa.DateTime(), nullable=True),
        sa.Column('related_hashtags', sa.JSON(), nullable=True),
        sa.Column('top_creators', sa.JSON(), nullable=True),
        sa.Column('geographic_distribution', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('last_analyzed', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['trend_id'], ['tiktok_trends.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for tiktok_hashtags
    op.create_index('idx_tiktok_hashtag_trending', 'tiktok_hashtags', ['is_trending', 'trend_score'])
    op.create_index('idx_tiktok_hashtag_usage', 'tiktok_hashtags', ['total_videos', 'usage_velocity'])
    op.create_index('idx_tiktok_hashtag_seen', 'tiktok_hashtags', ['first_seen'])
    op.create_index(op.f('ix_tiktok_hashtags_hashtag'), 'tiktok_hashtags', ['hashtag'], unique=True)
    op.create_index(op.f('ix_tiktok_hashtags_normalized_hashtag'), 'tiktok_hashtags', ['normalized_hashtag'])
    op.create_index(op.f('ix_tiktok_hashtags_trend_id'), 'tiktok_hashtags', ['trend_id'])
    op.create_index(op.f('ix_tiktok_hashtags_is_trending'), 'tiktok_hashtags', ['is_trending'])

    # Create tiktok_sounds table
    op.create_table(
        'tiktok_sounds',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('sound_id', sa.String(length=100), nullable=False),
        sa.Column('trend_id', sa.Integer(), nullable=True),
        sa.Column('title', sa.String(length=500), nullable=True),
        sa.Column('artist', sa.String(length=200), nullable=True),
        sa.Column('duration', sa.Integer(), nullable=True),
        sa.Column('sound_url', sa.String(length=500), nullable=True),
        sa.Column('total_videos', sa.BigInteger(), nullable=True),
        sa.Column('total_views', sa.BigInteger(), nullable=True),
        sa.Column('usage_velocity', sa.Float(), nullable=True),
        sa.Column('is_trending', sa.Boolean(), nullable=True),
        sa.Column('trend_score', sa.Float(), nullable=True),
        sa.Column('first_detected', sa.DateTime(), nullable=True),
        sa.Column('peak_usage', sa.DateTime(), nullable=True),
        sa.Column('genre', sa.String(length=100), nullable=True),
        sa.Column('mood', sa.String(length=100), nullable=True),
        sa.Column('tempo', sa.String(length=50), nullable=True),
        sa.Column('is_original', sa.Boolean(), nullable=True),
        sa.Column('is_licensed', sa.Boolean(), nullable=True),
        sa.Column('top_creators', sa.JSON(), nullable=True),
        sa.Column('usage_patterns', sa.JSON(), nullable=True),
        sa.Column('geographic_distribution', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('last_analyzed', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['trend_id'], ['tiktok_trends.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for tiktok_sounds
    op.create_index('idx_tiktok_sound_trending', 'tiktok_sounds', ['is_trending', 'trend_score'])
    op.create_index('idx_tiktok_sound_artist', 'tiktok_sounds', ['artist'])
    op.create_index('idx_tiktok_sound_genre', 'tiktok_sounds', ['genre'])
    op.create_index('idx_tiktok_sound_usage', 'tiktok_sounds', ['total_videos', 'usage_velocity'])
    op.create_index(op.f('ix_tiktok_sounds_sound_id'), 'tiktok_sounds', ['sound_id'], unique=True)
    op.create_index(op.f('ix_tiktok_sounds_trend_id'), 'tiktok_sounds', ['trend_id'])
    op.create_index(op.f('ix_tiktok_sounds_is_trending'), 'tiktok_sounds', ['is_trending'])

    # Create tiktok_scraping_jobs table
    op.create_table(
        'tiktok_scraping_jobs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('job_id', sa.String(length=100), nullable=False),
        sa.Column('apify_run_id', sa.String(length=100), nullable=True),
        sa.Column('job_type', sa.String(length=50), nullable=False),
        sa.Column('target', sa.String(length=500), nullable=True),
        sa.Column('parameters', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('progress', sa.Float(), nullable=True),
        sa.Column('videos_scraped', sa.Integer(), nullable=True),
        sa.Column('trends_identified', sa.Integer(), nullable=True),
        sa.Column('hashtags_discovered', sa.Integer(), nullable=True),
        sa.Column('sounds_tracked', sa.Integer(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('estimated_duration', sa.Integer(), nullable=True),
        sa.Column('error_count', sa.Integer(), nullable=True),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=True),
        sa.Column('max_retries', sa.Integer(), nullable=True),
        sa.Column('data_quality_score', sa.Float(), nullable=True),
        sa.Column('validation_errors', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for tiktok_scraping_jobs
    op.create_index('idx_tiktok_job_status_type', 'tiktok_scraping_jobs', ['status', 'job_type'])
    op.create_index('idx_tiktok_job_created', 'tiktok_scraping_jobs', ['created_at'])
    op.create_index('idx_tiktok_job_completed', 'tiktok_scraping_jobs', ['completed_at'])
    op.create_index(op.f('ix_tiktok_scraping_jobs_job_id'), 'tiktok_scraping_jobs', ['job_id'], unique=True)
    op.create_index(op.f('ix_tiktok_scraping_jobs_apify_run_id'), 'tiktok_scraping_jobs', ['apify_run_id'], unique=True)
    op.create_index(op.f('ix_tiktok_scraping_jobs_job_type'), 'tiktok_scraping_jobs', ['job_type'])
    op.create_index(op.f('ix_tiktok_scraping_jobs_status'), 'tiktok_scraping_jobs', ['status'])

    # Create tiktok_analytics table
    op.create_table(
        'tiktok_analytics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('date', sa.DateTime(), nullable=False),
        sa.Column('period_type', sa.String(length=20), nullable=True),
        sa.Column('total_trends', sa.Integer(), nullable=True),
        sa.Column('emerging_trends', sa.Integer(), nullable=True),
        sa.Column('declining_trends', sa.Integer(), nullable=True),
        sa.Column('peak_trends', sa.Integer(), nullable=True),
        sa.Column('total_videos_analyzed', sa.BigInteger(), nullable=True),
        sa.Column('avg_engagement_rate', sa.Float(), nullable=True),
        sa.Column('top_content_categories', sa.JSON(), nullable=True),
        sa.Column('total_hashtags', sa.Integer(), nullable=True),
        sa.Column('trending_hashtags', sa.Integer(), nullable=True),
        sa.Column('top_hashtags', sa.JSON(), nullable=True),
        sa.Column('total_sounds', sa.Integer(), nullable=True),
        sa.Column('trending_sounds', sa.Integer(), nullable=True),
        sa.Column('top_sounds', sa.JSON(), nullable=True),
        sa.Column('avg_viral_score', sa.Float(), nullable=True),
        sa.Column('detection_accuracy', sa.Float(), nullable=True),
        sa.Column('processing_time', sa.Float(), nullable=True),
        sa.Column('top_regions', sa.JSON(), nullable=True),
        sa.Column('regional_trends', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for tiktok_analytics
    op.create_index('idx_tiktok_analytics_date_period', 'tiktok_analytics', ['date', 'period_type'])
    op.create_unique_constraint('uq_tiktok_analytics_date_period', 'tiktok_analytics', ['date', 'period_type'])


def downgrade():
    # Drop tables in reverse order of creation
    op.drop_table('tiktok_analytics')
    op.drop_table('tiktok_scraping_jobs')
    op.drop_table('tiktok_sounds')
    op.drop_table('tiktok_hashtags')
    op.drop_table('tiktok_videos')
    op.drop_table('tiktok_trends')