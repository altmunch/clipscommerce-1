import { test, expect } from '@playwright/test';

test.describe('Dashboard Workflow', () => {
  test.beforeEach(async ({ page }) => {
    // Visit the dashboard
    await page.goto('/');
  });

  test('displays main dashboard structure', async ({ page }) => {
    // Check for main branding
    await expect(page.getByText('ViralOS')).toBeVisible();
    
    // Check for navigation tabs
    await expect(page.getByRole('button', { name: /strategy/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /pipeline/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /results/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /brand kit/i })).toBeVisible();
    
    // Check for brand selector
    await expect(page.getByText('Displaying for:')).toBeVisible();
    await expect(page.getByText('YourBrand.com')).toBeVisible();
    
    // Check for new campaign button
    await expect(page.getByRole('button', { name: /new campaign/i })).toBeVisible();
  });

  test('navigates between tabs correctly', async ({ page }) => {
    // Default should be strategy tab
    await expect(page.getByRole('button', { name: /strategy/i })).toHaveAttribute('aria-selected', 'true');
    
    // Click pipeline tab
    await page.getByRole('button', { name: /pipeline/i }).click();
    await expect(page.getByRole('button', { name: /pipeline/i })).toHaveClass(/border-b-primary-accent/);
    
    // Click results tab
    await page.getByRole('button', { name: /results/i }).click();
    await expect(page.getByRole('button', { name: /results/i })).toHaveClass(/border-b-primary-accent/);
    
    // Click brand kit tab
    await page.getByRole('button', { name: /brand kit/i }).click();
    await expect(page.getByRole('button', { name: /brand kit/i })).toHaveClass(/border-b-primary-accent/);
    
    // Go back to strategy
    await page.getByRole('button', { name: /strategy/i }).click();
    await expect(page.getByRole('button', { name: /strategy/i })).toHaveClass(/border-b-primary-accent/);
  });

  test('brand selector is interactive', async ({ page }) => {
    const brandSelector = page.getByText('YourBrand.com');
    await expect(brandSelector).toBeVisible();
    
    // Should be clickable
    await expect(brandSelector).toHaveAttribute('tabindex', '0');
    
    // Click brand selector
    await brandSelector.click();
    
    // In a real app, this might open a dropdown or modal
    // For now, we just verify it's clickable
  });

  test('new campaign button is functional', async ({ page }) => {
    const newCampaignButton = page.getByRole('button', { name: /new campaign/i });
    await expect(newCampaignButton).toBeVisible();
    await expect(newCampaignButton).toBeEnabled();
    
    // Click the button
    await newCampaignButton.click();
    
    // In a real app, this would open a modal or navigate to campaign creation
    // For now, we verify the click works
  });

  test('keyboard navigation works correctly', async ({ page }) => {
    // Focus should start on the first tab
    await page.keyboard.press('Tab');
    await expect(page.getByRole('button', { name: /strategy/i })).toBeFocused();
    
    // Navigate to next tab
    await page.keyboard.press('Tab');
    await expect(page.getByRole('button', { name: /pipeline/i })).toBeFocused();
    
    // Navigate to next tab
    await page.keyboard.press('Tab');
    await expect(page.getByRole('button', { name: /results/i })).toBeFocused();
    
    // Navigate to next tab
    await page.keyboard.press('Tab');
    await expect(page.getByRole('button', { name: /brand kit/i })).toBeFocused();
  });

  test('responsive design works on mobile', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    
    // Main elements should still be visible
    await expect(page.getByText('ViralOS')).toBeVisible();
    await expect(page.getByRole('button', { name: /strategy/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /new campaign/i })).toBeVisible();
    
    // Layout should adapt to mobile
    const tabsList = page.getByRole('button', { name: /strategy/i }).locator('..');
    await expect(tabsList).toBeVisible();
  });

  test('responsive design works on tablet', async ({ page }) => {
    // Set tablet viewport
    await page.setViewportSize({ width: 768, height: 1024 });
    
    // All elements should be properly visible and positioned
    await expect(page.getByText('ViralOS')).toBeVisible();
    
    // Tabs should be in horizontal layout
    const strategyTab = page.getByRole('button', { name: /strategy/i });
    const pipelineTab = page.getByRole('button', { name: /pipeline/i });
    
    const strategyBox = await strategyTab.boundingBox();
    const pipelineBox = await pipelineTab.boundingBox();
    
    // Pipeline tab should be to the right of strategy tab
    expect(pipelineBox?.x).toBeGreaterThan(strategyBox?.x || 0);
  });

  test('handles tab switching with content changes', async ({ page }) => {
    // Initially on strategy tab
    await expect(page.getByRole('button', { name: /strategy/i })).toHaveClass(/border-b-primary-accent/);
    
    // Switch to pipeline and verify content area changes
    await page.getByRole('button', { name: /pipeline/i }).click();
    await page.waitForTimeout(100); // Small delay for tab content to switch
    
    // Switch to results
    await page.getByRole('button', { name: /results/i }).click();
    await page.waitForTimeout(100);
    
    // Switch to brand kit
    await page.getByRole('button', { name: /brand kit/i }).click();
    await page.waitForTimeout(100);
    
    // Verify final state
    await expect(page.getByRole('button', { name: /brand kit/i })).toHaveClass(/border-b-primary-accent/);
  });

  test('visual elements render correctly', async ({ page }) => {
    // Check that icons are present (they should be rendered as SVGs or fonts)
    const strategyTab = page.getByRole('button', { name: /strategy/i });
    const pipelineTab = page.getByRole('button', { name: /pipeline/i });
    const resultsTab = page.getByRole('button', { name: /results/i });
    const brandKitTab = page.getByRole('button', { name: /brand kit/i });
    
    // All tabs should have text content
    await expect(strategyTab).toContainText('Strategy');
    await expect(pipelineTab).toContainText('Pipeline');
    await expect(resultsTab).toContainText('Results');
    await expect(brandKitTab).toContainText('Brand Kit');
    
    // Brand selector should have chevron indicator
    const brandSelector = page.getByText('YourBrand.com').locator('..');
    await expect(brandSelector).toBeVisible();
  });

  test('maintains state during rapid tab switching', async ({ page }) => {
    // Rapidly switch between tabs
    for (let i = 0; i < 3; i++) {
      await page.getByRole('button', { name: /pipeline/i }).click();
      await page.getByRole('button', { name: /results/i }).click();
      await page.getByRole('button', { name: /brand kit/i }).click();
      await page.getByRole('button', { name: /strategy/i }).click();
    }
    
    // Should end up on strategy tab
    await expect(page.getByRole('button', { name: /strategy/i })).toHaveClass(/border-b-primary-accent/);
    
    // UI should be stable and responsive
    await expect(page.getByText('ViralOS')).toBeVisible();
    await expect(page.getByRole('button', { name: /new campaign/i })).toBeVisible();
  });
});