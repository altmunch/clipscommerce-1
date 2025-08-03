"""Add social media models

Revision ID: 006_add_social_media_models
Revises: 005_add_analytics_models
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '006_add_social_media_models'
down_revision = '005_add_analytics_models'
branch_labels = None
depends_on = None


def upgrade():
    # Create enum types
    op.execute("CREATE TYPE platformtype AS ENUM ('tiktok', 'instagram', 'facebook')")
    op.execute("CREATE TYPE accountstatus AS ENUM ('active', 'inactive', 'suspended', 'pending_verification', 'error')")
    op.execute("CREATE TYPE poststatus AS ENUM ('draft', 'scheduled', 'publishing', 'published', 'failed', 'deleted')")
    op.execute("CREATE TYPE contenttype AS ENUM ('video', 'image', 'reel', 'story', 'carousel')")
    
    # Create social_media_accounts table
    op.create_table('social_media_accounts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('brand_id', sa.Integer(), nullable=False),
        sa.Column('platform', postgresql.ENUM('tiktok', 'instagram', 'facebook', name='platformtype'), nullable=False),
        sa.Column('username', sa.String(), nullable=False),
        sa.Column('display_name', sa.String(), nullable=True),
        sa.Column('profile_picture_url', sa.String(), nullable=True),
        sa.Column('platform_account_id', sa.String(), nullable=False),
        sa.Column('business_account_id', sa.String(), nullable=True),
        sa.Column('access_token', sa.Text(), nullable=True),
        sa.Column('refresh_token', sa.Text(), nullable=True),
        sa.Column('token_expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', postgresql.ENUM('active', 'inactive', 'suspended', 'pending_verification', 'error', name='accountstatus'), nullable=True),
        sa.Column('is_business_account', sa.Boolean(), nullable=True),
        sa.Column('is_verified', sa.Boolean(), nullable=True),
        sa.Column('follower_count', sa.Integer(), nullable=True),
        sa.Column('following_count', sa.Integer(), nullable=True),
        sa.Column('posting_settings', sa.JSON(), nullable=True),
        sa.Column('analytics_settings', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_sync_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['brand_id'], ['brands.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('platform_account_id')
    )
    op.create_index(op.f('ix_social_media_accounts_id'), 'social_media_accounts', ['id'], unique=False)
    
    # Create social_media_posts table
    op.create_table('social_media_posts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('account_id', sa.Integer(), nullable=False),
        sa.Column('video_project_id', sa.Integer(), nullable=True),
        sa.Column('campaign_id', sa.Integer(), nullable=True),
        sa.Column('platform_post_id', sa.String(), nullable=True),
        sa.Column('post_url', sa.String(), nullable=True),
        sa.Column('content_type', postgresql.ENUM('video', 'image', 'reel', 'story', 'carousel', name='contenttype'), nullable=False),
        sa.Column('caption', sa.Text(), nullable=True),
        sa.Column('hashtags', sa.JSON(), nullable=True),
        sa.Column('mentions', sa.JSON(), nullable=True),
        sa.Column('location_tag', sa.String(), nullable=True),
        sa.Column('media_urls', sa.JSON(), nullable=True),
        sa.Column('thumbnail_url', sa.String(), nullable=True),
        sa.Column('duration', sa.Integer(), nullable=True),
        sa.Column('status', postgresql.ENUM('draft', 'scheduled', 'publishing', 'published', 'failed', 'deleted', name='poststatus'), nullable=True),
        sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('privacy_settings', sa.JSON(), nullable=True),
        sa.Column('audience_targeting', sa.JSON(), nullable=True),
        sa.Column('post_settings', sa.JSON(), nullable=True),
        sa.Column('view_count', sa.Integer(), nullable=True),
        sa.Column('like_count', sa.Integer(), nullable=True),
        sa.Column('comment_count', sa.Integer(), nullable=True),
        sa.Column('share_count', sa.Integer(), nullable=True),
        sa.Column('save_count', sa.Integer(), nullable=True),
        sa.Column('engagement_rate', sa.Float(), nullable=True),
        sa.Column('reach', sa.Integer(), nullable=True),
        sa.Column('impressions', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['account_id'], ['social_media_accounts.id'], ),
        sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id'], ),
        sa.ForeignKeyConstraint(['video_project_id'], ['video_projects.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_social_media_posts_id'), 'social_media_posts', ['id'], unique=False)
    
    # Create social_media_analytics table
    op.create_table('social_media_analytics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('account_id', sa.Integer(), nullable=False),
        sa.Column('post_id', sa.Integer(), nullable=True),
        sa.Column('date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('period_type', sa.String(), nullable=True),
        sa.Column('views', sa.Integer(), nullable=True),
        sa.Column('likes', sa.Integer(), nullable=True),
        sa.Column('comments', sa.Integer(), nullable=True),
        sa.Column('shares', sa.Integer(), nullable=True),
        sa.Column('saves', sa.Integer(), nullable=True),
        sa.Column('reach', sa.Integer(), nullable=True),
        sa.Column('impressions', sa.Integer(), nullable=True),
        sa.Column('unique_viewers', sa.Integer(), nullable=True),
        sa.Column('engagement_rate', sa.Float(), nullable=True),
        sa.Column('like_rate', sa.Float(), nullable=True),
        sa.Column('comment_rate', sa.Float(), nullable=True),
        sa.Column('share_rate', sa.Float(), nullable=True),
        sa.Column('audience_demographics', sa.JSON(), nullable=True),
        sa.Column('audience_interests', sa.JSON(), nullable=True),
        sa.Column('top_territories', sa.JSON(), nullable=True),
        sa.Column('watch_time_total', sa.Integer(), nullable=True),
        sa.Column('average_watch_time', sa.Float(), nullable=True),
        sa.Column('completion_rate', sa.Float(), nullable=True),
        sa.Column('profile_visits', sa.Integer(), nullable=True),
        sa.Column('website_clicks', sa.Integer(), nullable=True),
        sa.Column('follows_gained', sa.Integer(), nullable=True),
        sa.Column('platform_metrics', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['account_id'], ['social_media_accounts.id'], ),
        sa.ForeignKeyConstraint(['post_id'], ['social_media_posts.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_social_media_analytics_id'), 'social_media_analytics', ['id'], unique=False)
    
    # Create posting_schedules table
    op.create_table('posting_schedules',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('account_id', sa.Integer(), nullable=False),
        sa.Column('brand_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('timezone', sa.String(), nullable=True),
        sa.Column('posting_times', sa.JSON(), nullable=True),
        sa.Column('posting_frequency', sa.JSON(), nullable=True),
        sa.Column('content_types', sa.JSON(), nullable=True),
        sa.Column('hashtag_strategy', sa.JSON(), nullable=True),
        sa.Column('caption_templates', sa.JSON(), nullable=True),
        sa.Column('auto_optimize_timing', sa.Boolean(), nullable=True),
        sa.Column('auto_optimize_hashtags', sa.Boolean(), nullable=True),
        sa.Column('auto_optimize_captions', sa.Boolean(), nullable=True),
        sa.Column('posts_scheduled', sa.Integer(), nullable=True),
        sa.Column('posts_published', sa.Integer(), nullable=True),
        sa.Column('average_engagement', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_posting_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['account_id'], ['social_media_accounts.id'], ),
        sa.ForeignKeyConstraint(['brand_id'], ['brands.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_posting_schedules_id'), 'posting_schedules', ['id'], unique=False)
    
    # Create social_media_webhooks table
    op.create_table('social_media_webhooks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('account_id', sa.Integer(), nullable=True),
        sa.Column('post_id', sa.Integer(), nullable=True),
        sa.Column('platform', postgresql.ENUM('tiktok', 'instagram', 'facebook', name='platformtype'), nullable=False),
        sa.Column('event_type', sa.String(), nullable=False),
        sa.Column('webhook_id', sa.String(), nullable=True),
        sa.Column('event_data', sa.JSON(), nullable=False),
        sa.Column('processed', sa.Boolean(), nullable=True),
        sa.Column('processing_error', sa.Text(), nullable=True),
        sa.Column('received_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['account_id'], ['social_media_accounts.id'], ),
        sa.ForeignKeyConstraint(['post_id'], ['social_media_posts.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_social_media_webhooks_id'), 'social_media_webhooks', ['id'], unique=False)
    
    # Create cross_platform_campaigns table
    op.create_table('cross_platform_campaigns',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('brand_id', sa.Integer(), nullable=False),
        sa.Column('campaign_id', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('platforms', sa.JSON(), nullable=False),
        sa.Column('platform_settings', sa.JSON(), nullable=True),
        sa.Column('content_strategy', sa.JSON(), nullable=True),
        sa.Column('hashtag_strategy', sa.JSON(), nullable=True),
        sa.Column('posting_strategy', sa.JSON(), nullable=True),
        sa.Column('total_posts', sa.Integer(), nullable=True),
        sa.Column('total_engagement', sa.Integer(), nullable=True),
        sa.Column('total_reach', sa.Integer(), nullable=True),
        sa.Column('budget', sa.Float(), nullable=True),
        sa.Column('spent', sa.Float(), nullable=True),
        sa.Column('revenue_attributed', sa.Float(), nullable=True),
        sa.Column('roi', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('start_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('end_date', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['brand_id'], ['brands.id'], ),
        sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_cross_platform_campaigns_id'), 'cross_platform_campaigns', ['id'], unique=False)
    
    # Set default values for existing columns
    op.execute("UPDATE social_media_accounts SET status = 'active' WHERE status IS NULL")
    op.execute("UPDATE social_media_accounts SET is_business_account = false WHERE is_business_account IS NULL")
    op.execute("UPDATE social_media_accounts SET is_verified = false WHERE is_verified IS NULL")
    op.execute("UPDATE social_media_accounts SET follower_count = 0 WHERE follower_count IS NULL")
    op.execute("UPDATE social_media_accounts SET following_count = 0 WHERE following_count IS NULL")
    
    op.execute("UPDATE social_media_posts SET status = 'draft' WHERE status IS NULL")
    op.execute("UPDATE social_media_posts SET view_count = 0 WHERE view_count IS NULL")
    op.execute("UPDATE social_media_posts SET like_count = 0 WHERE like_count IS NULL")
    op.execute("UPDATE social_media_posts SET comment_count = 0 WHERE comment_count IS NULL")
    op.execute("UPDATE social_media_posts SET share_count = 0 WHERE share_count IS NULL")
    op.execute("UPDATE social_media_posts SET save_count = 0 WHERE save_count IS NULL")
    op.execute("UPDATE social_media_posts SET engagement_rate = 0.0 WHERE engagement_rate IS NULL")
    op.execute("UPDATE social_media_posts SET reach = 0 WHERE reach IS NULL")
    op.execute("UPDATE social_media_posts SET impressions = 0 WHERE impressions IS NULL")
    op.execute("UPDATE social_media_posts SET retry_count = 0 WHERE retry_count IS NULL")
    
    op.execute("UPDATE social_media_analytics SET period_type = 'daily' WHERE period_type IS NULL")
    op.execute("UPDATE social_media_analytics SET views = 0 WHERE views IS NULL")
    op.execute("UPDATE social_media_analytics SET likes = 0 WHERE likes IS NULL")
    op.execute("UPDATE social_media_analytics SET comments = 0 WHERE comments IS NULL")
    op.execute("UPDATE social_media_analytics SET shares = 0 WHERE shares IS NULL")
    op.execute("UPDATE social_media_analytics SET saves = 0 WHERE saves IS NULL")
    op.execute("UPDATE social_media_analytics SET reach = 0 WHERE reach IS NULL")
    op.execute("UPDATE social_media_analytics SET impressions = 0 WHERE impressions IS NULL")
    op.execute("UPDATE social_media_analytics SET unique_viewers = 0 WHERE unique_viewers IS NULL")
    op.execute("UPDATE social_media_analytics SET engagement_rate = 0.0 WHERE engagement_rate IS NULL")
    op.execute("UPDATE social_media_analytics SET like_rate = 0.0 WHERE like_rate IS NULL")
    op.execute("UPDATE social_media_analytics SET comment_rate = 0.0 WHERE comment_rate IS NULL")
    op.execute("UPDATE social_media_analytics SET share_rate = 0.0 WHERE share_rate IS NULL")
    op.execute("UPDATE social_media_analytics SET watch_time_total = 0 WHERE watch_time_total IS NULL")
    op.execute("UPDATE social_media_analytics SET average_watch_time = 0.0 WHERE average_watch_time IS NULL")
    op.execute("UPDATE social_media_analytics SET completion_rate = 0.0 WHERE completion_rate IS NULL")
    op.execute("UPDATE social_media_analytics SET profile_visits = 0 WHERE profile_visits IS NULL")
    op.execute("UPDATE social_media_analytics SET website_clicks = 0 WHERE website_clicks IS NULL")
    op.execute("UPDATE social_media_analytics SET follows_gained = 0 WHERE follows_gained IS NULL")
    
    op.execute("UPDATE posting_schedules SET is_active = true WHERE is_active IS NULL")
    op.execute("UPDATE posting_schedules SET timezone = 'UTC' WHERE timezone IS NULL")
    op.execute("UPDATE posting_schedules SET auto_optimize_timing = true WHERE auto_optimize_timing IS NULL")
    op.execute("UPDATE posting_schedules SET auto_optimize_hashtags = true WHERE auto_optimize_hashtags IS NULL")
    op.execute("UPDATE posting_schedules SET auto_optimize_captions = false WHERE auto_optimize_captions IS NULL")
    op.execute("UPDATE posting_schedules SET posts_scheduled = 0 WHERE posts_scheduled IS NULL")
    op.execute("UPDATE posting_schedules SET posts_published = 0 WHERE posts_published IS NULL")
    op.execute("UPDATE posting_schedules SET average_engagement = 0.0 WHERE average_engagement IS NULL")
    
    op.execute("UPDATE social_media_webhooks SET processed = false WHERE processed IS NULL")
    
    op.execute("UPDATE cross_platform_campaigns SET status = 'active' WHERE status IS NULL")
    op.execute("UPDATE cross_platform_campaigns SET total_posts = 0 WHERE total_posts IS NULL")
    op.execute("UPDATE cross_platform_campaigns SET total_engagement = 0 WHERE total_engagement IS NULL")
    op.execute("UPDATE cross_platform_campaigns SET total_reach = 0 WHERE total_reach IS NULL")
    op.execute("UPDATE cross_platform_campaigns SET budget = 0.0 WHERE budget IS NULL")
    op.execute("UPDATE cross_platform_campaigns SET spent = 0.0 WHERE spent IS NULL")
    op.execute("UPDATE cross_platform_campaigns SET revenue_attributed = 0.0 WHERE revenue_attributed IS NULL")
    op.execute("UPDATE cross_platform_campaigns SET roi = 0.0 WHERE roi IS NULL")


def downgrade():
    # Drop tables in reverse order
    op.drop_index(op.f('ix_cross_platform_campaigns_id'), table_name='cross_platform_campaigns')
    op.drop_table('cross_platform_campaigns')
    
    op.drop_index(op.f('ix_social_media_webhooks_id'), table_name='social_media_webhooks')
    op.drop_table('social_media_webhooks')
    
    op.drop_index(op.f('ix_posting_schedules_id'), table_name='posting_schedules')
    op.drop_table('posting_schedules')
    
    op.drop_index(op.f('ix_social_media_analytics_id'), table_name='social_media_analytics')
    op.drop_table('social_media_analytics')
    
    op.drop_index(op.f('ix_social_media_posts_id'), table_name='social_media_posts')
    op.drop_table('social_media_posts')
    
    op.drop_index(op.f('ix_social_media_accounts_id'), table_name='social_media_accounts')
    op.drop_table('social_media_accounts')
    
    # Drop enum types
    op.execute("DROP TYPE IF EXISTS platformtype")
    op.execute("DROP TYPE IF EXISTS accountstatus")
    op.execute("DROP TYPE IF EXISTS poststatus")
    op.execute("DROP TYPE IF EXISTS contenttype")