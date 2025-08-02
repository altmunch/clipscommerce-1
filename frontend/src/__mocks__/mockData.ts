// Mock data for testing
export const mockBrands = [
  {
    id: 'brand-1',
    name: 'TechCorp',
    url: 'https://techcorp.com',
    status: 'active',
    created_at: '2024-01-01T00:00:00Z',
    brandKit: {
      colors: ['#3B82F6', '#EF4444', '#10B981'],
      fonts: ['Inter', 'Roboto'],
      voice: 'Professional and innovative',
      values: ['Innovation', 'Quality', 'Customer Focus'],
      target_audience: 'Tech-savvy professionals aged 25-45',
      content_pillars: ['Product Updates', 'Industry Insights', 'Customer Success'],
    }
  },
  {
    id: 'brand-2',
    name: 'FashionForward',
    url: 'https://fashionforward.com',
    status: 'active',
    created_at: '2024-01-02T00:00:00Z',
    brandKit: {
      colors: ['#EC4899', '#F59E0B', '#8B5CF6'],
      fonts: ['Playfair Display', 'Open Sans'],
      voice: 'Trendy and inspirational',
      values: ['Style', 'Sustainability', 'Inclusivity'],
      target_audience: 'Fashion enthusiasts aged 18-35',
      content_pillars: ['Style Tips', 'Sustainability', 'Brand Collaborations'],
    }
  }
]

export const mockCampaigns = [
  {
    id: 'campaign-1',
    brand_id: 'brand-1',
    name: 'Q1 Product Launch',
    description: 'Launch campaign for new product line',
    status: 'active',
    start_date: '2024-01-01',
    end_date: '2024-03-31',
    budget: 50000,
    created_at: '2024-01-01T00:00:00Z'
  },
  {
    id: 'campaign-2',
    brand_id: 'brand-2',
    name: 'Summer Collection',
    description: 'Summer fashion collection promotion',
    status: 'draft',
    start_date: '2024-06-01',
    end_date: '2024-08-31',
    budget: 30000,
    created_at: '2024-05-01T00:00:00Z'
  }
]

export const mockContent = {
  ideas: [
    {
      id: 'idea-1',
      brand_id: 'brand-1',
      campaign_id: 'campaign-1',
      title: '5 Tech Trends Reshaping Business',
      description: 'Educational video about emerging technologies',
      type: 'educational',
      platform: 'youtube',
      estimated_views: 10000,
      engagement_score: 8.5,
      created_at: '2024-01-01T00:00:00Z'
    },
    {
      id: 'idea-2',
      brand_id: 'brand-1',
      campaign_id: 'campaign-1',
      title: 'Behind the Scenes: Product Development',
      description: 'Documentary-style content about product creation',
      type: 'behind_scenes',
      platform: 'tiktok',
      estimated_views: 50000,
      engagement_score: 9.2,
      created_at: '2024-01-02T00:00:00Z'
    }
  ],
  performance: [
    {
      id: 'content-1',
      title: '5 Tech Trends Reshaping Business',
      platform: 'YouTube',
      views: 12500,
      engagement_rate: 8.9,
      shares: 145,
      comments: 89,
      likes: 1100,
      published_at: '2024-01-15T00:00:00Z',
      performance_score: 'A+'
    },
    {
      id: 'content-2',
      title: 'Behind the Scenes: Product Development',
      platform: 'TikTok',
      views: 48000,
      engagement_rate: 12.3,
      shares: 890,
      comments: 234,
      likes: 5600,
      published_at: '2024-01-20T00:00:00Z',
      performance_score: 'A'
    }
  ]
}

export const mockKpis = {
  total_views: 125000,
  total_engagement: 8950,
  avg_engagement_rate: 9.8,
  total_followers_gained: 1250,
  conversion_rate: 3.2,
  roi: 245.5,
  period_comparison: {
    views_change: 15.2,
    engagement_change: 22.1,
    followers_change: 8.7
  }
}

export const mockInsights = [
  {
    type: 'trend',
    title: 'Video Engagement Peak',
    description: 'Your videos perform best between 6-8 PM on weekdays',
    priority: 'high',
    actionable: true,
    recommendation: 'Schedule future content for optimal timing'
  },
  {
    type: 'content',
    title: 'Educational Content Outperforms',
    description: 'Educational videos have 34% higher engagement than promotional content',
    priority: 'medium',
    actionable: true,
    recommendation: 'Increase educational content ratio to 60%'
  },
  {
    type: 'audience',
    title: 'Growing Mobile Audience',
    description: '78% of your audience watches on mobile devices',
    priority: 'medium',
    actionable: true,
    recommendation: 'Optimize content for mobile viewing'
  }
]

// Test utilities
export const createMockBrand = (overrides: Partial<typeof mockBrands[0]> = {}) => ({
  ...mockBrands[0],
  ...overrides,
  id: overrides.id || `brand-${Date.now()}`
})

export const createMockCampaign = (overrides: Partial<typeof mockCampaigns[0]> = {}) => ({
  ...mockCampaigns[0],
  ...overrides,
  id: overrides.id || `campaign-${Date.now()}`
})

export const createMockIdea = (overrides: Partial<typeof mockContent.ideas[0]> = {}) => ({
  ...mockContent.ideas[0],
  ...overrides,
  id: overrides.id || `idea-${Date.now()}`
})

export const createMockUser = (overrides: Partial<{id: string; email: string; name: string}> = {}) => ({
  id: 'user-1',
  email: 'test@example.com',
  name: 'Test User',
  ...overrides
})