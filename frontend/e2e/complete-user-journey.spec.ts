/**
 * E2E tests for complete user journeys through the ViralOS platform
 * including brand onboarding, content creation, and analytics workflows.
 */

import { test, expect, Page } from '@playwright/test'

test.describe('Complete User Journey', () => {
  
  test.beforeEach(async ({ page }) => {
    // Set up authentication and base state
    await page.goto('/')
    
    // Mock API responses for consistent testing
    await page.route('**/api/v1/**', async route => {
      const url = new URL(route.request().url())
      const path = url.pathname
      
      if (path.includes('/brands') && route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify([
            {
              id: 'brand-1',
              name: 'TechCorp',
              url: 'https://techcorp.com',
              status: 'active'
            }
          ])
        })
      } else if (path.includes('/analyze-url') && route.request().method() === 'POST') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            status: 'success',
            job_id: 'job-123',
            brand_info: {
              name: 'Amazing Tech Brand',
              description: 'Innovative technology products',
              logo_url: 'https://example.com/logo.png',
              colors: ['#FF6B6B', '#4ECDC4'],
              voice: 'innovative and friendly'
            },
            products: [
              {
                name: 'Smart Widget Pro',
                description: 'Revolutionary smart widget with AI capabilities',
                price: 199.99,
                images: ['https://example.com/widget.jpg']
              }
            ]
          })
        })
      } else if (path.includes('/video-generation/projects') && route.request().method() === 'POST') {
        await route.fulfill({
          status: 201,
          contentType: 'application/json',
          body: JSON.stringify({
            id: 'video-project-123',
            status: 'completed',
            video_url: 'https://storage.example.com/generated_video.mp4',
            thumbnail_url: 'https://storage.example.com/thumbnail.jpg',
            duration: 30
          })
        })
      } else if (path.includes('/social-media/post-multi-platform') && route.request().method() === 'POST') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            tiktok: { status: 'success', post_id: 'tiktok_123', share_url: 'https://tiktok.com/@brand/video/123' },
            instagram: { status: 'success', post_id: 'instagram_456', permalink: 'https://instagram.com/p/ABC123/' }
          })
        })
      } else {
        await route.continue()
      }
    })
  })

  test('Brand Onboarding to First Video Generation', async ({ page }) => {
    // Step 1: Navigate to dashboard
    await expect(page.locator('text=ViralOS')).toBeVisible()
    await expect(page.locator('text=Strategy')).toBeVisible()
    
    // Step 2: Start brand analysis
    await page.click('[data-testid="new-campaign-button"]')
    await expect(page.locator('text=Enter Brand URL')).toBeVisible()
    
    // Step 3: Enter brand URL
    const urlInput = page.locator('input[placeholder*="Enter brand URL"]')
    await urlInput.fill('https://amazingtech.com')
    await page.click('button:has-text("Analyze Brand")')
    
    // Step 4: Wait for and verify analysis results
    await expect(page.locator('text=Brand Analysis Complete')).toBeVisible({ timeout: 10000 })
    await expect(page.locator('text=Amazing Tech Brand')).toBeVisible()
    await expect(page.locator('text=Smart Widget Pro')).toBeVisible()
    
    // Step 5: Proceed to video generation
    await page.click('button:has-text("Generate Video")')
    await expect(page.locator('text=Video Generation')).toBeVisible()
    
    // Step 6: Configure video settings
    await page.selectOption('select[name="platform"]', 'tiktok')
    await page.fill('input[name="duration"]', '30')
    await page.selectOption('select[name="style"]', 'professional')
    
    // Step 7: Start video generation
    await page.click('button:has-text("Start Generation")')
    await expect(page.locator('text=Generating Video')).toBeVisible()
    
    // Step 8: Wait for video completion and verify result
    await expect(page.locator('text=Video Generated Successfully')).toBeVisible({ timeout: 30000 })
    await expect(page.locator('video')).toBeVisible()
    await expect(page.locator('button:has-text("Download Video")')).toBeVisible()
    
    // Step 9: Verify video details
    const videoDuration = await page.locator('[data-testid="video-duration"]').textContent()
    expect(videoDuration).toContain('30s')
  })

  test('Complete Content Creation and Social Media Posting', async ({ page }) => {
    // Start from video generation completion
    await completeVideoGeneration(page)
    
    // Step 1: Proceed to social media posting
    await page.click('button:has-text("Proceed to Posting")')
    await expect(page.locator('text=Social Media Posting')).toBeVisible()
    
    // Step 2: Configure platform-specific settings
    await page.check('input[name="platform-tiktok"]')
    await page.check('input[name="platform-instagram"]')
    
    // Step 3: Customize captions for each platform
    const tiktokCaption = page.locator('textarea[name="tiktok-caption"]')
    await tiktokCaption.fill('🔥 Amazing new tech! This will blow your mind! #viral #innovation #tech')
    
    const instagramCaption = page.locator('textarea[name="instagram-caption"]')
    await instagramCaption.fill('Discover the future of technology with our Smart Widget Pro ✨ Innovation meets design in this groundbreaking product. #innovation #technology #smartwidget #newproduct')
    
    // Step 4: Add hashtags
    const hashtagInput = page.locator('input[name="hashtags"]')
    await hashtagInput.fill('#innovation #tech #smartwidget #viral #trending')
    
    // Step 5: Schedule or post immediately
    await page.check('input[name="post-immediately"]')
    
    // Step 6: Post to platforms
    await page.click('button:has-text("Post to Platforms")')
    await expect(page.locator('text=Posting to Platforms')).toBeVisible()
    
    // Step 7: Verify posting results
    await expect(page.locator('text=Posted Successfully')).toBeVisible({ timeout: 15000 })
    await expect(page.locator('text=TikTok: Posted')).toBeVisible()
    await expect(page.locator('text=Instagram: Posted')).toBeVisible()
    
    // Step 8: Verify platform links
    const tiktokLink = page.locator('a:has-text("View on TikTok")')
    await expect(tiktokLink).toBeVisible()
    await expect(tiktokLink).toHaveAttribute('href', /tiktok\.com/)
    
    const instagramLink = page.locator('a:has-text("View on Instagram")')
    await expect(instagramLink).toBeVisible()
    await expect(instagramLink).toHaveAttribute('href', /instagram\.com/)
  })

  test('Analytics Dashboard and Performance Monitoring', async ({ page }) => {
    // Mock analytics data
    await page.route('**/api/v1/analytics/**', async route => {
      if (route.request().url().includes('kpis')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            total_views: 150000,
            total_engagement: 12500,
            avg_engagement_rate: 8.3,
            follower_growth: 250
          })
        })
      } else if (route.request().url().includes('chart-data')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
            data: [12000, 15000, 18000, 22000, 25000, 30000, 28000]
          })
        })
      } else {
        await route.continue()
      }
    })
    
    // Step 1: Navigate to Results tab
    await page.click('button:has-text("Results")')
    await expect(page.locator('text=Results')).toBeVisible()
    
    // Step 2: Verify KPI cards
    await expect(page.locator('[data-testid="total-views"]')).toContainText('150,000')
    await expect(page.locator('[data-testid="total-engagement"]')).toContainText('12,500')
    await expect(page.locator('[data-testid="engagement-rate"]')).toContainText('8.3%')
    await expect(page.locator('[data-testid="follower-growth"]')).toContainText('250')
    
    // Step 3: Interact with analytics charts
    const chartContainer = page.locator('[data-testid="analytics-chart"]')
    await expect(chartContainer).toBeVisible()
    
    // Step 4: Switch between different metrics
    await page.click('button:has-text("Views")')
    await expect(page.locator('text=View Analytics')).toBeVisible()
    
    await page.click('button:has-text("Engagement")')
    await expect(page.locator('text=Engagement Analytics')).toBeVisible()
    
    // Step 5: Test date range selector
    await page.click('[data-testid="date-range-selector"]')
    await page.click('text=Last 30 Days')
    await expect(page.locator('text=Showing data for last 30 days')).toBeVisible()
    
    // Step 6: Export analytics data
    await page.click('button:has-text("Export Data")')
    
    // Verify download was triggered (in real test, you'd check the actual download)
    const downloadPromise = page.waitForEvent('download')
    await page.click('button:has-text("Download CSV")')
    const download = await downloadPromise
    expect(download.suggestedFilename()).toContain('analytics')
  })

  test('Brand Kit Management and Customization', async ({ page }) => {
    // Mock brand kit data
    await page.route('**/api/v1/brands/**/brand-kit', async route => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            colors: ['#FF6B6B', '#4ECDC4', '#45B7D1'],
            fonts: ['Helvetica Neue', 'Arial'],
            voice: 'innovative and friendly',
            logo_url: 'https://example.com/logo.png',
            values: ['innovation', 'quality', 'sustainability']
          })
        })
      } else if (route.request().method() === 'PUT') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            id: 'brand-1',
            ...JSON.parse(await route.request().postData() || '{}')
          })
        })
      }
    })
    
    // Step 1: Navigate to Brand Kit tab
    await page.click('button:has-text("Brand Kit")')
    await expect(page.locator('text=Brand Kit')).toBeVisible()
    
    // Step 2: Verify current brand kit displays
    await expect(page.locator('[data-testid="brand-colors"]')).toBeVisible()
    await expect(page.locator('[data-testid="brand-fonts"]')).toBeVisible()
    await expect(page.locator('[data-testid="brand-voice"]')).toContainText('innovative and friendly')
    
    // Step 3: Edit brand colors
    await page.click('button:has-text("Edit Colors")')
    
    // Add a new color
    await page.click('[data-testid="add-color-button"]')
    const colorInput = page.locator('input[type="color"]').last()
    await colorInput.fill('#FF5722')
    
    // Step 4: Update brand voice
    await page.click('button:has-text("Edit Voice")')
    const voiceTextarea = page.locator('textarea[name="brand-voice"]')
    await voiceTextarea.clear()
    await voiceTextarea.fill('innovative, friendly, and cutting-edge')
    
    // Step 5: Add brand values
    await page.click('button:has-text("Edit Values")')
    const valueInput = page.locator('input[name="new-value"]')
    await valueInput.fill('customer-centric')
    await page.click('button:has-text("Add Value")')
    
    // Step 6: Save changes
    await page.click('button:has-text("Save Brand Kit")')
    await expect(page.locator('text=Brand Kit Updated Successfully')).toBeVisible()
    
    // Step 7: Verify changes were applied
    await expect(page.locator('[data-testid="brand-voice"]')).toContainText('cutting-edge')
    await expect(page.locator('text=customer-centric')).toBeVisible()
  })

  test('Error Handling and Recovery', async ({ page }) => {
    // Step 1: Test network error handling
    await page.route('**/api/v1/brands/**/analyze-url', async route => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Internal server error' })
      })
    })
    
    // Try to analyze a brand URL
    await page.click('[data-testid="new-campaign-button"]')
    const urlInput = page.locator('input[placeholder*="Enter brand URL"]')
    await urlInput.fill('https://errortest.com')
    await page.click('button:has-text("Analyze Brand")')
    
    // Verify error message
    await expect(page.locator('text=Something went wrong')).toBeVisible()
    await expect(page.locator('button:has-text("Try Again")')).toBeVisible()
    
    // Step 2: Test retry mechanism
    // Reset route to success
    await page.route('**/api/v1/brands/**/analyze-url', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'success',
          brand_info: { name: 'Recovered Brand' },
          products: []
        })
      })
    })
    
    await page.click('button:has-text("Try Again")')
    await expect(page.locator('text=Recovered Brand')).toBeVisible()
    
    // Step 3: Test form validation
    await page.goto('/')
    await page.click('[data-testid="new-campaign-button"]')
    
    // Try to submit without URL
    await page.click('button:has-text("Analyze Brand")')
    await expect(page.locator('text=Please enter a valid URL')).toBeVisible()
    
    // Try invalid URL
    const invalidUrlInput = page.locator('input[placeholder*="Enter brand URL"]')
    await invalidUrlInput.fill('not-a-url')
    await page.click('button:has-text("Analyze Brand")')
    await expect(page.locator('text=Please enter a valid URL')).toBeVisible()
  })

  test('Responsive Design and Mobile Experience', async ({ page }) => {
    // Test mobile viewport
    await page.setViewportSize({ width: 375, height: 667 })
    
    // Step 1: Verify mobile navigation
    await expect(page.locator('[data-testid="mobile-menu-button"]')).toBeVisible()
    await page.click('[data-testid="mobile-menu-button"]')
    await expect(page.locator('[data-testid="mobile-menu"]')).toBeVisible()
    
    // Step 2: Test mobile tab navigation
    await page.click('text=Strategy')
    await expect(page.locator('[data-testid="strategy-tab"]')).toBeVisible()
    
    await page.click('text=Pipeline')
    await expect(page.locator('[data-testid="pipeline-tab"]')).toBeVisible()
    
    // Step 3: Test mobile form interactions
    await page.click('[data-testid="new-campaign-button"]')
    const mobileUrlInput = page.locator('input[placeholder*="Enter brand URL"]')
    await expect(mobileUrlInput).toBeVisible()
    
    // Verify mobile-friendly input
    await mobileUrlInput.fill('https://mobile-test.com')
    await expect(mobileUrlInput).toHaveValue('https://mobile-test.com')
    
    // Step 4: Test tablet viewport
    await page.setViewportSize({ width: 768, height: 1024 })
    await expect(page.locator('[data-testid="mobile-menu-button"]')).not.toBeVisible()
    await expect(page.locator('text=ViralOS')).toBeVisible()
  })

  test('Performance and Loading States', async ({ page }) => {
    // Monitor page load performance
    const startTime = Date.now()
    await page.goto('/')
    const loadTime = Date.now() - startTime
    
    // Verify page loads within reasonable time
    expect(loadTime).toBeLessThan(3000)
    
    // Test loading states
    await page.route('**/api/v1/**', async route => {
      // Add delay to test loading states
      await new Promise(resolve => setTimeout(resolve, 2000))
      await route.continue()
    })
    
    // Start an operation that shows loading state
    await page.click('[data-testid="new-campaign-button"]')
    const urlInput = page.locator('input[placeholder*="Enter brand URL"]')
    await urlInput.fill('https://loadingtest.com')
    await page.click('button:has-text("Analyze Brand")')
    
    // Verify loading indicators appear
    await expect(page.locator('[data-testid="loading-spinner"]')).toBeVisible()
    await expect(page.locator('text=Analyzing Brand')).toBeVisible()
    
    // Verify loading progress indicators
    await expect(page.locator('[role="progressbar"]')).toBeVisible()
    await expect(page.locator('text=Extracting brand information')).toBeVisible()
  })
})

// Helper functions
async function completeVideoGeneration(page: Page) {
  await page.click('[data-testid="new-campaign-button"]')
  const urlInput = page.locator('input[placeholder*="Enter brand URL"]')
  await urlInput.fill('https://amazingtech.com')
  await page.click('button:has-text("Analyze Brand")')
  
  await expect(page.locator('text=Amazing Tech Brand')).toBeVisible()
  await page.click('button:has-text("Generate Video")')
  
  await page.selectOption('select[name="platform"]', 'tiktok')
  await page.click('button:has-text("Start Generation")')
  
  await expect(page.locator('text=Video Generated Successfully')).toBeVisible({ timeout: 30000 })
}

// Performance monitoring helper
async function measurePageLoadTime(page: Page, url: string): Promise<number> {
  const startTime = Date.now()
  await page.goto(url)
  await page.waitForLoadState('networkidle')
  return Date.now() - startTime
}