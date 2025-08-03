"""Add product and scraping models

Revision ID: 002_add_product_and_scraping_models
Revises: 001_initial_migration
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002_add_product_and_scraping_models'
down_revision = '001_initial_migration'
branch_labels = None
depends_on = None


def upgrade():
    # Create products table
    op.create_table('products',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('brand_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('short_description', sa.Text(), nullable=True),
        sa.Column('sku', sa.String(), nullable=True),
        sa.Column('brand_name', sa.String(), nullable=True),
        sa.Column('category', sa.String(), nullable=True),
        sa.Column('price', sa.Float(), nullable=True),
        sa.Column('original_price', sa.Float(), nullable=True),
        sa.Column('currency', sa.String(length=3), nullable=True),
        sa.Column('sale_price', sa.Float(), nullable=True),
        sa.Column('discount_percentage', sa.Float(), nullable=True),
        sa.Column('price_range', sa.JSON(), nullable=True),
        sa.Column('availability', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('source_url', sa.String(), nullable=False),
        sa.Column('source_domain', sa.String(), nullable=True),
        sa.Column('platform_type', sa.String(), nullable=True),
        sa.Column('images', sa.JSON(), nullable=True),
        sa.Column('variants', sa.JSON(), nullable=True),
        sa.Column('attributes', sa.JSON(), nullable=True),
        sa.Column('features', sa.JSON(), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('reviews_data', sa.JSON(), nullable=True),
        sa.Column('shipping_info', sa.JSON(), nullable=True),
        sa.Column('seller_info', sa.JSON(), nullable=True),
        sa.Column('social_proof', sa.JSON(), nullable=True),
        sa.Column('scraping_metadata', sa.JSON(), nullable=True),
        sa.Column('data_quality_score', sa.Float(), nullable=True),
        sa.Column('first_seen_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('last_updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('last_scraped_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['brand_id'], ['brands.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for products
    op.create_index('idx_product_brand_category', 'products', ['brand_id', 'category'])
    op.create_index('idx_product_price_range', 'products', ['price', 'currency'])
    op.create_index('idx_product_availability', 'products', ['availability', 'is_active'])
    op.create_index('idx_product_source', 'products', ['source_domain', 'platform_type'])
    op.create_index('idx_product_updated', 'products', ['last_updated_at'])
    op.create_index(op.f('ix_products_brand_name'), 'products', ['brand_name'], unique=False)
    op.create_index(op.f('ix_products_category'), 'products', ['category'], unique=False)
    op.create_index(op.f('ix_products_id'), 'products', ['id'], unique=False)
    op.create_index(op.f('ix_products_sku'), 'products', ['sku'], unique=False)
    op.create_index(op.f('ix_products_source_domain'), 'products', ['source_domain'], unique=False)
    op.create_index(op.f('ix_products_source_url'), 'products', ['source_url'], unique=False)
    op.create_index(op.f('ix_products_availability'), 'products', ['availability'], unique=False)
    op.create_index(op.f('ix_products_platform_type'), 'products', ['platform_type'], unique=False)

    # Create product_price_history table
    op.create_table('product_price_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('price', sa.Float(), nullable=False),
        sa.Column('original_price', sa.Float(), nullable=True),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('discount_percentage', sa.Float(), nullable=True),
        sa.Column('availability', sa.String(), nullable=True),
        sa.Column('in_stock', sa.Boolean(), nullable=True),
        sa.Column('source_url', sa.String(), nullable=True),
        sa.Column('promotion_info', sa.JSON(), nullable=True),
        sa.Column('recorded_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for price history
    op.create_index('idx_price_history_product_date', 'product_price_history', ['product_id', 'recorded_at'])
    op.create_index('idx_price_history_price', 'product_price_history', ['price', 'currency'])
    op.create_index(op.f('ix_product_price_history_id'), 'product_price_history', ['id'], unique=False)
    op.create_index(op.f('ix_product_price_history_recorded_at'), 'product_price_history', ['recorded_at'], unique=False)

    # Create product_competitors table
    op.create_table('product_competitors',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('competitor_product_id', sa.Integer(), nullable=False),
        sa.Column('similarity_score', sa.Float(), nullable=True),
        sa.Column('price_difference', sa.Float(), nullable=True),
        sa.Column('feature_comparison', sa.JSON(), nullable=True),
        sa.Column('competition_type', sa.String(), nullable=True),
        sa.Column('match_criteria', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('last_compared_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['competitor_product_id'], ['products.id'], ),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for competitors
    op.create_index('idx_unique_competition', 'product_competitors', ['product_id', 'competitor_product_id'], unique=True)
    op.create_index('idx_competitor_similarity', 'product_competitors', ['similarity_score'])
    op.create_index(op.f('ix_product_competitors_id'), 'product_competitors', ['id'], unique=False)

    # Create scraping_jobs table
    op.create_table('scraping_jobs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('brand_id', sa.Integer(), nullable=True),
        sa.Column('job_id', sa.String(), nullable=True),
        sa.Column('job_type', sa.String(), nullable=False),
        sa.Column('target_urls', sa.JSON(), nullable=True),
        sa.Column('scraping_config', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('progress', sa.Integer(), nullable=True),
        sa.Column('products_found', sa.Integer(), nullable=True),
        sa.Column('products_created', sa.Integer(), nullable=True),
        sa.Column('products_updated', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=True),
        sa.Column('max_retries', sa.Integer(), nullable=True),
        sa.Column('pages_scraped', sa.Integer(), nullable=True),
        sa.Column('total_processing_time', sa.Float(), nullable=True),
        sa.Column('avg_page_load_time', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['brand_id'], ['brands.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for scraping jobs
    op.create_index('idx_scraping_job_status', 'scraping_jobs', ['status', 'created_at'])
    op.create_index('idx_scraping_job_brand', 'scraping_jobs', ['brand_id', 'job_type'])
    op.create_index(op.f('ix_scraping_jobs_id'), 'scraping_jobs', ['id'], unique=False)
    op.create_index(op.f('ix_scraping_jobs_job_id'), 'scraping_jobs', ['job_id'], unique=True)
    op.create_index(op.f('ix_scraping_jobs_status'), 'scraping_jobs', ['status'], unique=False)

    # Create competitor_brands table
    op.create_table('competitor_brands',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('brand_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('url', sa.String(), nullable=False),
        sa.Column('logo_url', sa.String(), nullable=True),
        sa.Column('similarity_score', sa.Float(), nullable=True),
        sa.Column('threat_level', sa.String(), nullable=True),
        sa.Column('competition_type', sa.String(), nullable=True),
        sa.Column('estimated_size', sa.String(), nullable=True),
        sa.Column('market_share', sa.Float(), nullable=True),
        sa.Column('pricing_strategy', sa.String(), nullable=True),
        sa.Column('brand_colors', sa.JSON(), nullable=True),
        sa.Column('brand_voice', sa.JSON(), nullable=True),
        sa.Column('target_audience', sa.JSON(), nullable=True),
        sa.Column('unique_selling_points', sa.JSON(), nullable=True),
        sa.Column('social_followers', sa.JSON(), nullable=True),
        sa.Column('social_engagement', sa.JSON(), nullable=True),
        sa.Column('products_tracked', sa.Integer(), nullable=True),
        sa.Column('avg_product_price', sa.Float(), nullable=True),
        sa.Column('price_positioning', sa.String(), nullable=True),
        sa.Column('monitoring_enabled', sa.Boolean(), nullable=True),
        sa.Column('last_analyzed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('next_analysis_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('discovered_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['brand_id'], ['brands.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for competitor brands
    op.create_index('idx_competitor_brand', 'competitor_brands', ['brand_id', 'similarity_score'])
    op.create_index('idx_competitor_threat', 'competitor_brands', ['threat_level', 'competition_type'])
    op.create_index('idx_competitor_monitoring', 'competitor_brands', ['monitoring_enabled', 'next_analysis_at'])
    op.create_index(op.f('ix_competitor_brands_id'), 'competitor_brands', ['id'], unique=False)

    # Create scraping_sessions table
    op.create_table('scraping_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('job_id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.String(), nullable=True),
        sa.Column('scraper_type', sa.String(), nullable=True),
        sa.Column('use_proxy', sa.Boolean(), nullable=True),
        sa.Column('proxy_info', sa.JSON(), nullable=True),
        sa.Column('user_agent', sa.String(), nullable=True),
        sa.Column('target_url', sa.String(), nullable=False),
        sa.Column('target_domain', sa.String(), nullable=True),
        sa.Column('platform_detected', sa.String(), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=True),
        sa.Column('data_extracted', sa.JSON(), nullable=True),
        sa.Column('products_found', sa.Integer(), nullable=True),
        sa.Column('response_time', sa.Float(), nullable=True),
        sa.Column('page_load_time', sa.Float(), nullable=True),
        sa.Column('data_quality_score', sa.Float(), nullable=True),
        sa.Column('error_type', sa.String(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('bot_detection', sa.JSON(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['job_id'], ['scraping_jobs.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for scraping sessions
    op.create_index('idx_session_job', 'scraping_sessions', ['job_id', 'success'])
    op.create_index('idx_session_domain', 'scraping_sessions', ['target_domain', 'started_at'])
    op.create_index('idx_session_performance', 'scraping_sessions', ['response_time', 'data_quality_score'])
    op.create_index(op.f('ix_scraping_sessions_id'), 'scraping_sessions', ['id'], unique=False)
    op.create_index(op.f('ix_scraping_sessions_session_id'), 'scraping_sessions', ['session_id'], unique=True)
    op.create_index(op.f('ix_scraping_sessions_target_domain'), 'scraping_sessions', ['target_domain'], unique=False)

    # Add new columns to existing brands table
    op.add_column('brands', sa.Column('industry', sa.String(), nullable=True))
    op.add_column('brands', sa.Column('target_audience', sa.JSON(), nullable=True))
    op.add_column('brands', sa.Column('unique_value_proposition', sa.Text(), nullable=True))
    op.add_column('brands', sa.Column('competitors', sa.JSON(), nullable=True))
    op.add_column('brands', sa.Column('market_position', sa.JSON(), nullable=True))
    op.add_column('brands', sa.Column('product_count', sa.Integer(), nullable=True))
    op.add_column('brands', sa.Column('avg_price_range', sa.JSON(), nullable=True))
    op.add_column('brands', sa.Column('main_categories', sa.JSON(), nullable=True))
    op.add_column('brands', sa.Column('scraping_config', sa.JSON(), nullable=True))
    op.add_column('brands', sa.Column('last_full_scrape', sa.DateTime(timezone=True), nullable=True))
    
    # Create index for industry
    op.create_index(op.f('ix_brands_industry'), 'brands', ['industry'], unique=False)


def downgrade():
    # Drop indexes first
    op.drop_index(op.f('ix_brands_industry'), table_name='brands')
    
    # Remove columns from brands table
    op.drop_column('brands', 'last_full_scrape')
    op.drop_column('brands', 'scraping_config')
    op.drop_column('brands', 'main_categories')
    op.drop_column('brands', 'avg_price_range')
    op.drop_column('brands', 'product_count')
    op.drop_column('brands', 'market_position')
    op.drop_column('brands', 'competitors')
    op.drop_column('brands', 'unique_value_proposition')
    op.drop_column('brands', 'target_audience')
    op.drop_column('brands', 'industry')
    
    # Drop scraping_sessions table and indexes
    op.drop_index(op.f('ix_scraping_sessions_target_domain'), table_name='scraping_sessions')
    op.drop_index(op.f('ix_scraping_sessions_session_id'), table_name='scraping_sessions')
    op.drop_index(op.f('ix_scraping_sessions_id'), table_name='scraping_sessions')
    op.drop_index('idx_session_performance', table_name='scraping_sessions')
    op.drop_index('idx_session_domain', table_name='scraping_sessions')
    op.drop_index('idx_session_job', table_name='scraping_sessions')
    op.drop_table('scraping_sessions')
    
    # Drop competitor_brands table and indexes
    op.drop_index(op.f('ix_competitor_brands_id'), table_name='competitor_brands')
    op.drop_index('idx_competitor_monitoring', table_name='competitor_brands')
    op.drop_index('idx_competitor_threat', table_name='competitor_brands')
    op.drop_index('idx_competitor_brand', table_name='competitor_brands')
    op.drop_table('competitor_brands')
    
    # Drop scraping_jobs table and indexes
    op.drop_index(op.f('ix_scraping_jobs_status'), table_name='scraping_jobs')
    op.drop_index(op.f('ix_scraping_jobs_job_id'), table_name='scraping_jobs')
    op.drop_index(op.f('ix_scraping_jobs_id'), table_name='scraping_jobs')
    op.drop_index('idx_scraping_job_brand', table_name='scraping_jobs')
    op.drop_index('idx_scraping_job_status', table_name='scraping_jobs')
    op.drop_table('scraping_jobs')
    
    # Drop product_competitors table and indexes
    op.drop_index(op.f('ix_product_competitors_id'), table_name='product_competitors')
    op.drop_index('idx_competitor_similarity', table_name='product_competitors')
    op.drop_index('idx_unique_competition', table_name='product_competitors')
    op.drop_table('product_competitors')
    
    # Drop product_price_history table and indexes
    op.drop_index(op.f('ix_product_price_history_recorded_at'), table_name='product_price_history')
    op.drop_index(op.f('ix_product_price_history_id'), table_name='product_price_history')
    op.drop_index('idx_price_history_price', table_name='product_price_history')
    op.drop_index('idx_price_history_product_date', table_name='product_price_history')
    op.drop_table('product_price_history')
    
    # Drop products table and indexes
    op.drop_index(op.f('ix_products_platform_type'), table_name='products')
    op.drop_index(op.f('ix_products_availability'), table_name='products')
    op.drop_index(op.f('ix_products_source_url'), table_name='products')
    op.drop_index(op.f('ix_products_source_domain'), table_name='products')
    op.drop_index(op.f('ix_products_sku'), table_name='products')
    op.drop_index(op.f('ix_products_id'), table_name='products')
    op.drop_index(op.f('ix_products_category'), table_name='products')
    op.drop_index(op.f('ix_products_brand_name'), table_name='products')
    op.drop_index('idx_product_updated', table_name='products')
    op.drop_index('idx_product_source', table_name='products')
    op.drop_index('idx_product_availability', table_name='products')
    op.drop_index('idx_product_price_range', table_name='products')
    op.drop_index('idx_product_brand_category', table_name='products')
    op.drop_table('products')