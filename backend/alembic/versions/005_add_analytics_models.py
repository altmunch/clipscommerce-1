"""Add analytics models

Revision ID: 005_add_analytics_models
Revises: 004_add_video_generation_models
Create Date: 2024-12-19 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '005_add_analytics_models'
down_revision = '004_add_video_generation_models'
branch_labels = None
depends_on = None

def upgrade():
    # Create platform type enum
    platform_type_enum = postgresql.ENUM('tiktok', 'instagram', 'youtube', 'facebook', name='platformtype')
    platform_type_enum.create(op.get_bind())
    
    # Create performance category enum  
    performance_category_enum = postgresql.ENUM('hook', 'content', 'cta', 'overall', name='performancecategory')
    performance_category_enum.create(op.get_bind())
    
    # Create experiment status enum
    experiment_status_enum = postgresql.ENUM('draft', 'running', 'completed', 'paused', 'cancelled', name='experimentstatus')
    experiment_status_enum.create(op.get_bind())
    
    # Create video_performance_predictions table
    op.create_table('video_performance_predictions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('video_id', sa.Integer(), nullable=False),
        sa.Column('platform', platform_type_enum, nullable=False),
        sa.Column('overall_score', sa.Float(), nullable=False),
        sa.Column('confidence_interval', sa.Float(), nullable=False),
        sa.Column('predicted_views', sa.Integer(), nullable=True),
        sa.Column('predicted_engagement_rate', sa.Float(), nullable=True),
        sa.Column('hook_score', sa.Float(), nullable=False),
        sa.Column('content_score', sa.Float(), nullable=False),
        sa.Column('cta_score', sa.Float(), nullable=False),
        sa.Column('visual_analysis', sa.JSON(), nullable=True),
        sa.Column('audio_analysis', sa.JSON(), nullable=True),
        sa.Column('recommendations', sa.JSON(), nullable=True),
        sa.Column('model_version', sa.String(length=50), nullable=False),
        sa.Column('processing_time', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['video_id'], ['videos.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_video_performance_predictions_id'), 'video_performance_predictions', ['id'], unique=False)
    
    # Create trend_recommendations table
    op.create_table('trend_recommendations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('brand_id', sa.Integer(), nullable=False),
        sa.Column('platform', platform_type_enum, nullable=False),
        sa.Column('trend_type', sa.String(length=50), nullable=False),
        sa.Column('trend_id', sa.String(length=255), nullable=False),
        sa.Column('trend_name', sa.String(length=500), nullable=False),
        sa.Column('trend_description', sa.Text(), nullable=True),
        sa.Column('trend_volume', sa.Integer(), nullable=False),
        sa.Column('growth_rate', sa.Float(), nullable=False),
        sa.Column('virality_score', sa.Float(), nullable=False),
        sa.Column('relevance_score', sa.Float(), nullable=False),
        sa.Column('audio_url', sa.String(length=1000), nullable=True),
        sa.Column('audio_duration', sa.Float(), nullable=True),
        sa.Column('audio_mood', sa.String(length=100), nullable=True),
        sa.Column('audio_bpm', sa.Integer(), nullable=True),
        sa.Column('copyright_status', sa.String(length=50), nullable=True),
        sa.Column('peak_usage_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('estimated_decay_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('recommended_usage_window', sa.JSON(), nullable=True),
        sa.Column('discovered_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('last_updated', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['brand_id'], ['brands.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_trend_recommendations_id'), 'trend_recommendations', ['id'], unique=False)
    
    # Create ab_test_experiments table
    op.create_table('ab_test_experiments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('campaign_id', sa.Integer(), nullable=False),
        sa.Column('brand_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('hypothesis', sa.Text(), nullable=False),
        sa.Column('status', experiment_status_enum, nullable=True),
        sa.Column('traffic_split', sa.JSON(), nullable=False),
        sa.Column('success_metrics', sa.JSON(), nullable=False),
        sa.Column('minimum_sample_size', sa.Integer(), nullable=False),
        sa.Column('confidence_level', sa.Float(), nullable=True),
        sa.Column('statistical_power', sa.Float(), nullable=True),
        sa.Column('start_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('end_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('planned_duration_days', sa.Integer(), nullable=False),
        sa.Column('current_sample_size', sa.Integer(), nullable=True),
        sa.Column('statistical_significance', sa.Float(), nullable=True),
        sa.Column('winner_variant', sa.String(length=100), nullable=True),
        sa.Column('confidence_interval', sa.JSON(), nullable=True),
        sa.Column('results_summary', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['brand_id'], ['brands.id'], ),
        sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ab_test_experiments_id'), 'ab_test_experiments', ['id'], unique=False)
    
    # Create ab_test_variants table
    op.create_table('ab_test_variants',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('experiment_id', sa.Integer(), nullable=False),
        sa.Column('video_id', sa.Integer(), nullable=False),
        sa.Column('variant_name', sa.String(length=100), nullable=False),
        sa.Column('variant_type', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('modifications', sa.JSON(), nullable=False),
        sa.Column('generation_prompt', sa.Text(), nullable=True),
        sa.Column('impressions', sa.Integer(), nullable=True),
        sa.Column('clicks', sa.Integer(), nullable=True),
        sa.Column('conversions', sa.Integer(), nullable=True),
        sa.Column('engagement_rate', sa.Float(), nullable=True),
        sa.Column('cost_per_result', sa.Float(), nullable=True),
        sa.Column('conversion_rate', sa.Float(), nullable=True),
        sa.Column('confidence_interval_lower', sa.Float(), nullable=True),
        sa.Column('confidence_interval_upper', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['experiment_id'], ['ab_test_experiments.id'], ),
        sa.ForeignKeyConstraint(['video_id'], ['videos.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ab_test_variants_id'), 'ab_test_variants', ['id'], unique=False)
    
    # Create video_analytics table
    op.create_table('video_analytics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('video_id', sa.Integer(), nullable=False),
        sa.Column('platform', platform_type_enum, nullable=False),
        sa.Column('views', sa.Integer(), nullable=True),
        sa.Column('likes', sa.Integer(), nullable=True),
        sa.Column('shares', sa.Integer(), nullable=True),
        sa.Column('comments', sa.Integer(), nullable=True),
        sa.Column('saves', sa.Integer(), nullable=True),
        sa.Column('avg_watch_time', sa.Float(), nullable=True),
        sa.Column('completion_rate', sa.Float(), nullable=True),
        sa.Column('engagement_rate', sa.Float(), nullable=True),
        sa.Column('click_through_rate', sa.Float(), nullable=True),
        sa.Column('audience_demographics', sa.JSON(), nullable=True),
        sa.Column('geographic_data', sa.JSON(), nullable=True),
        sa.Column('device_breakdown', sa.JSON(), nullable=True),
        sa.Column('traffic_sources', sa.JSON(), nullable=True),
        sa.Column('hourly_performance', sa.JSON(), nullable=True),
        sa.Column('daily_performance', sa.JSON(), nullable=True),
        sa.Column('recorded_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('data_source', sa.String(length=100), nullable=False),
        sa.ForeignKeyConstraint(['video_id'], ['videos.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_video_analytics_id'), 'video_analytics', ['id'], unique=False)
    
    # Create model_performance_metrics table
    op.create_table('model_performance_metrics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('model_name', sa.String(length=100), nullable=False),
        sa.Column('model_version', sa.String(length=50), nullable=False),
        sa.Column('accuracy', sa.Float(), nullable=False),
        sa.Column('precision', sa.Float(), nullable=False),
        sa.Column('recall', sa.Float(), nullable=False),
        sa.Column('f1_score', sa.Float(), nullable=False),
        sa.Column('mae', sa.Float(), nullable=True),
        sa.Column('rmse', sa.Float(), nullable=True),
        sa.Column('test_size', sa.Integer(), nullable=False),
        sa.Column('test_period_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('test_period_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('feature_importance', sa.JSON(), nullable=True),
        sa.Column('hyperparameters', sa.JSON(), nullable=True),
        sa.Column('training_duration', sa.Float(), nullable=True),
        sa.Column('evaluated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_model_performance_metrics_id'), 'model_performance_metrics', ['id'], unique=False)

def downgrade():
    # Drop tables
    op.drop_index(op.f('ix_model_performance_metrics_id'), table_name='model_performance_metrics')
    op.drop_table('model_performance_metrics')
    op.drop_index(op.f('ix_video_analytics_id'), table_name='video_analytics')
    op.drop_table('video_analytics')
    op.drop_index(op.f('ix_ab_test_variants_id'), table_name='ab_test_variants')
    op.drop_table('ab_test_variants')
    op.drop_index(op.f('ix_ab_test_experiments_id'), table_name='ab_test_experiments')
    op.drop_table('ab_test_experiments')
    op.drop_index(op.f('ix_trend_recommendations_id'), table_name='trend_recommendations')
    op.drop_table('trend_recommendations')
    op.drop_index(op.f('ix_video_performance_predictions_id'), table_name='video_performance_predictions')
    op.drop_table('video_performance_predictions')
    
    # Drop enums
    op.execute('DROP TYPE experimentstatus')
    op.execute('DROP TYPE performancecategory')
    op.execute('DROP TYPE platformtype')