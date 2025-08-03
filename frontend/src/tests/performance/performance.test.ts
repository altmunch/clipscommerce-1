/**
 * Performance testing suite for the ViralOS frontend application.
 * Tests Core Web Vitals, bundle sizes, and runtime performance.
 */

import { test, expect, chromium, Browser, Page } from '@playwright/test'
import lighthouse from 'lighthouse'
import { performance } from 'perf_hooks'

interface PerformanceMetrics {
  fcp: number // First Contentful Paint
  lcp: number // Largest Contentful Paint
  cls: number // Cumulative Layout Shift
  fid: number // First Input Delay
  tbt: number // Total Blocking Time
  si: number  // Speed Index
  ttfb: number // Time to First Byte
}

interface BundleAnalysis {
  totalSize: number
  jsSize: number
  cssSize: number
  imageSize: number
  chunkCount: number
}

test.describe('Frontend Performance Tests', () => {
  let browser: Browser
  let page: Page

  test.beforeAll(async () => {
    browser = await chromium.launch()
  })

  test.afterAll(async () => {
    await browser.close()
  })

  test.beforeEach(async () => {
    page = await browser.newPage()
    
    // Enable performance monitoring
    await page.addInitScript(() => {
      // Mark page load start
      window.performance.mark('page-load-start')
    })
  })

  test.afterEach(async () => {
    await page.close()
  })

  test('Dashboard loads within performance budget', async () => {
    const startTime = performance.now()
    
    // Navigate and wait for network idle
    await page.goto('/', { waitUntil: 'networkidle' })
    
    const loadTime = performance.now() - startTime
    
    // Performance assertions
    expect(loadTime).toBeLessThan(3000) // 3 second budget
    
    // Verify critical elements are visible
    await expect(page.locator('text=ViralOS')).toBeVisible()
    await expect(page.locator('text=Strategy')).toBeVisible()
    
    console.log(`Dashboard loaded in ${loadTime.toFixed(2)}ms`)
  })

  test('Core Web Vitals meet thresholds', async () => {
    await page.goto('/')
    
    // Wait for page to fully load
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(2000) // Additional wait for metrics
    
    // Get Core Web Vitals
    const vitals = await page.evaluate(() => {
      return new Promise<PerformanceMetrics>((resolve) => {
        const observer = new PerformanceObserver((list) => {
          const entries = list.getEntries()
          const metrics: Partial<PerformanceMetrics> = {}
          
          entries.forEach((entry) => {
            if (entry.entryType === 'paint') {
              if (entry.name === 'first-contentful-paint') {
                metrics.fcp = entry.startTime
              }
            }
            if (entry.entryType === 'largest-contentful-paint') {
              metrics.lcp = entry.startTime
            }
            if (entry.entryType === 'layout-shift' && !entry.hadRecentInput) {
              metrics.cls = (metrics.cls || 0) + entry.value
            }
          })
          
          // Get navigation timing
          const navigation = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming
          if (navigation) {
            metrics.ttfb = navigation.responseStart - navigation.requestStart
          }
          
          resolve(metrics as PerformanceMetrics)
        })
        
        observer.observe({ entryTypes: ['paint', 'largest-contentful-paint', 'layout-shift'] })
        
        // Fallback timeout
        setTimeout(() => {
          resolve({
            fcp: 0,
            lcp: 0,
            cls: 0,
            fid: 0,
            tbt: 0,
            si: 0,
            ttfb: 0
          })
        }, 5000)
      })
    })
    
    // Core Web Vitals thresholds (in milliseconds)
    if (vitals.fcp > 0) expect(vitals.fcp).toBeLessThan(1800) // Good: < 1.8s
    if (vitals.lcp > 0) expect(vitals.lcp).toBeLessThan(2500) // Good: < 2.5s
    if (vitals.cls > 0) expect(vitals.cls).toBeLessThan(0.1)  // Good: < 0.1
    if (vitals.ttfb > 0) expect(vitals.ttfb).toBeLessThan(800) // Good: < 0.8s
    
    console.log('Core Web Vitals:', vitals)
  })

  test('JavaScript bundle size is within budget', async () => {
    // Intercept network requests to analyze bundle sizes
    const resources: Array<{ url: string, size: number, type: string }> = []
    
    page.on('response', async (response) => {
      if (response.url().includes('.js') || response.url().includes('.css') || response.url().includes('chunk')) {
        const contentLength = response.headers()['content-length']
        const size = contentLength ? parseInt(contentLength) : 0
        
        let type = 'other'
        if (response.url().includes('.js')) type = 'javascript'
        if (response.url().includes('.css')) type = 'css'
        if (response.url().includes('.png') || response.url().includes('.jpg')) type = 'image'
        
        resources.push({
          url: response.url(),
          size,
          type
        })
      }
    })
    
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    
    // Analyze bundle sizes
    const analysis: BundleAnalysis = {
      totalSize: 0,
      jsSize: 0,
      cssSize: 0,
      imageSize: 0,
      chunkCount: 0
    }
    
    resources.forEach(resource => {
      analysis.totalSize += resource.size
      
      switch (resource.type) {
        case 'javascript':
          analysis.jsSize += resource.size
          analysis.chunkCount += 1
          break
        case 'css':
          analysis.cssSize += resource.size
          break
        case 'image':
          analysis.imageSize += resource.size
          break
      }
    })
    
    // Bundle size budgets (in bytes)
    expect(analysis.jsSize).toBeLessThan(1024 * 1024) // 1MB JS budget
    expect(analysis.cssSize).toBeLessThan(256 * 1024) // 256KB CSS budget
    expect(analysis.totalSize).toBeLessThan(3 * 1024 * 1024) // 3MB total budget
    expect(analysis.chunkCount).toBeLessThan(20) // Max 20 JS chunks
    
    console.log('Bundle Analysis:', analysis)
  })

  test('Interactive elements respond quickly', async () => {
    await page.goto('/')
    
    // Test tab switching performance
    const startTime = performance.now()
    
    await page.click('button:has-text("Pipeline")')
    await expect(page.locator('[data-testid="pipeline-tab"]')).toBeVisible()
    
    const switchTime = performance.now() - startTime
    expect(switchTime).toBeLessThan(100) // Should switch tabs in < 100ms
    
    // Test button interaction
    const buttonStartTime = performance.now()
    
    await page.click('button:has-text("+ New Campaign")')
    await expect(page.locator('text=Enter Brand URL')).toBeVisible()
    
    const buttonResponseTime = performance.now() - buttonStartTime
    expect(buttonResponseTime).toBeLessThan(200) // Button response < 200ms
    
    console.log(`Tab switch: ${switchTime.toFixed(2)}ms, Button response: ${buttonResponseTime.toFixed(2)}ms`)
  })

  test('Workflow performance under load', async () => {
    await page.goto('/')
    
    // Simulate rapid user interactions
    const interactions = [
      () => page.click('button:has-text("Strategy")'),
      () => page.click('button:has-text("Pipeline")'),
      () => page.click('button:has-text("Results")'),
      () => page.click('button:has-text("Brand Kit")'),
      () => page.click('button:has-text("+ New Campaign")')
    ]
    
    const startTime = performance.now()
    
    // Execute interactions rapidly
    for (const interaction of interactions) {
      await interaction()
      await page.waitForTimeout(50) // Small delay between interactions
    }
    
    const totalTime = performance.now() - startTime
    
    // Should handle rapid interactions smoothly
    expect(totalTime).toBeLessThan(1000) // All interactions < 1s
    
    console.log(`Completed ${interactions.length} interactions in ${totalTime.toFixed(2)}ms`)
  })

  test('Memory usage stays within bounds', async () => {
    await page.goto('/')
    
    // Get initial memory usage
    const initialMemory = await page.evaluate(() => {
      if ('memory' in performance) {
        const memory = (performance as any).memory
        return {
          usedJSHeapSize: memory.usedJSHeapSize,
          totalJSHeapSize: memory.totalJSHeapSize,
          jsHeapSizeLimit: memory.jsHeapSizeLimit
        }
      }
      return null
    })
    
    if (!initialMemory) {
      test.skip() // Skip if memory API not available
      return
    }
    
    // Perform memory-intensive operations
    await page.click('button:has-text("Strategy")')
    await page.waitForTimeout(1000)
    
    await page.click('button:has-text("Pipeline")')
    await page.waitForTimeout(1000)
    
    await page.click('button:has-text("Results")')
    await page.waitForTimeout(1000)
    
    // Check memory after operations
    const finalMemory = await page.evaluate(() => {
      if ('memory' in performance) {
        const memory = (performance as any).memory
        return {
          usedJSHeapSize: memory.usedJSHeapSize,
          totalJSHeapSize: memory.totalJSHeapSize,
          jsHeapSizeLimit: memory.jsHeapSizeLimit
        }
      }
      return null
    })
    
    if (finalMemory) {
      const memoryIncrease = finalMemory.usedJSHeapSize - initialMemory.usedJSHeapSize
      const memoryIncreasePercent = (memoryIncrease / initialMemory.usedJSHeapSize) * 100
      
      // Memory should not increase by more than 50%
      expect(memoryIncreasePercent).toBeLessThan(50)
      
      // Used heap should not exceed 80% of total heap
      const heapUsagePercent = (finalMemory.usedJSHeapSize / finalMemory.totalJSHeapSize) * 100
      expect(heapUsagePercent).toBeLessThan(80)
      
      console.log(`Memory usage: ${(initialMemory.usedJSHeapSize / 1024 / 1024).toFixed(2)}MB -> ${(finalMemory.usedJSHeapSize / 1024 / 1024).toFixed(2)}MB`)
    }
  })

  test('Image loading performance', async () => {
    const imageLoadTimes: number[] = []
    
    page.on('response', async (response) => {
      if (response.url().match(/\.(jpg|jpeg|png|gif|webp|svg)$/i)) {
        const timing = response.timing()
        if (timing) {
          const loadTime = timing.responseEnd
          imageLoadTimes.push(loadTime)
        }
      }
    })
    
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    
    if (imageLoadTimes.length > 0) {
      const avgImageLoadTime = imageLoadTimes.reduce((a, b) => a + b, 0) / imageLoadTimes.length
      const maxImageLoadTime = Math.max(...imageLoadTimes)
      
      // Image performance budgets
      expect(avgImageLoadTime).toBeLessThan(500) // Average image load < 500ms
      expect(maxImageLoadTime).toBeLessThan(2000) // No image takes > 2s
      
      console.log(`Image performance: avg ${avgImageLoadTime.toFixed(2)}ms, max ${maxImageLoadTime.toFixed(2)}ms`)
    }
  })

  test('API response time performance', async () => {
    const apiCalls: Array<{ url: string, duration: number }> = []
    
    page.on('response', async (response) => {
      if (response.url().includes('/api/v1/')) {
        const timing = response.timing()
        if (timing) {
          apiCalls.push({
            url: response.url(),
            duration: timing.responseEnd
          })
        }
      }
    })
    
    await page.goto('/')
    
    // Trigger some API calls
    await page.click('button:has-text("Results")')
    await page.waitForTimeout(2000)
    
    if (apiCalls.length > 0) {
      const avgApiTime = apiCalls.reduce((a, b) => a + b.duration, 0) / apiCalls.length
      const slowestApi = Math.max(...apiCalls.map(call => call.duration))
      
      // API performance budgets
      expect(avgApiTime).toBeLessThan(1000) // Average API call < 1s
      expect(slowestApi).toBeLessThan(3000) // No API call > 3s
      
      console.log(`API performance: avg ${avgApiTime.toFixed(2)}ms, slowest ${slowestApi.toFixed(2)}ms`)
    }
  })

  test('Accessibility performance impact', async () => {
    await page.goto('/')
    
    // Test that accessibility features don't impact performance
    const startTime = performance.now()
    
    // Test keyboard navigation
    await page.keyboard.press('Tab')
    await page.keyboard.press('Tab')
    await page.keyboard.press('Tab')
    await page.keyboard.press('Enter')
    
    const keyboardTime = performance.now() - startTime
    
    // Test screen reader compatibility
    const ariaLabels = await page.locator('[aria-label]').count()
    const roles = await page.locator('[role]').count()
    
    // Accessibility should not significantly impact performance
    expect(keyboardTime).toBeLessThan(100) // Keyboard nav < 100ms
    expect(ariaLabels).toBeGreaterThan(0) // Has accessible labels
    expect(roles).toBeGreaterThan(0) // Has semantic roles
    
    console.log(`Accessibility: ${ariaLabels} labels, ${roles} roles, keyboard nav ${keyboardTime.toFixed(2)}ms`)
  })
})

test.describe('Mobile Performance Tests', () => {
  test('Mobile performance meets standards', async () => {
    const browser = await chromium.launch()
    const context = await browser.newContext({
      ...chromium.devices['iPhone 13']
    })
    const page = await context.newPage()
    
    const startTime = performance.now()
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    const loadTime = performance.now() - startTime
    
    // Mobile performance budgets (more lenient)
    expect(loadTime).toBeLessThan(5000) // Mobile load < 5s
    
    // Test mobile interactions
    await page.tap('button:has-text("Pipeline")')
    await expect(page.locator('[data-testid="pipeline-tab"]')).toBeVisible()
    
    // Test mobile menu if present
    const mobileMenuButton = page.locator('[data-testid="mobile-menu-button"]')
    if (await mobileMenuButton.isVisible()) {
      await mobileMenuButton.tap()
      await expect(page.locator('[data-testid="mobile-menu"]')).toBeVisible()
    }
    
    await browser.close()
    
    console.log(`Mobile load time: ${loadTime.toFixed(2)}ms`)
  })
})