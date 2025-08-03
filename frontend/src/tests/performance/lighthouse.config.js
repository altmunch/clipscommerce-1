/**
 * Lighthouse configuration for performance testing
 * Tests Core Web Vitals and accessibility metrics
 */

module.exports = {
  extends: 'lighthouse:default',
  settings: {
    // Performance testing configuration
    onlyCategories: ['performance', 'accessibility', 'best-practices'],
    
    // Simulate various network conditions
    throttling: {
      rttMs: 150,
      throughputKbps: 1638.4,
      cpuSlowdownMultiplier: 4,
      requestLatencyMs: 562.5,
      downloadThroughputKbps: 1474.56,
      uploadThroughputKbps: 675.84
    },
    
    // Emulate mobile device
    emulatedFormFactor: 'mobile',
    
    // Skip certain audits that aren't relevant
    skipAudits: [
      'uses-http2',
      'canonical',
      'robots-txt'
    ]
  },
  
  audits: [
    // Core Web Vitals
    'largest-contentful-paint',
    'first-contentful-paint',
    'cumulative-layout-shift',
    'first-input-delay',
    'total-blocking-time',
    'speed-index',
    
    // Performance audits
    'unused-javascript',
    'unused-css-rules',
    'unminified-css',
    'unminified-javascript',
    'efficient-animated-content',
    'legacy-javascript',
    'modern-image-formats',
    'uses-optimized-images',
    'uses-webp-images',
    'uses-text-compression',
    'uses-responsive-images',
    'render-blocking-resources',
    'redirects',
    'uses-rel-preconnect',
    'uses-rel-preload',
    'critical-request-chains',
    'user-timings',
    'bootup-time',
    'mainthread-work-breakdown',
    'dom-size',
    'font-display',
    'resource-summary',
    'third-party-summary',
    'third-party-facades',
    'largest-contentful-paint-element',
    'layout-shift-elements',
    'uses-long-cache-ttl',
    'total-byte-weight',
    
    // Accessibility audits
    'accesskeys',
    'aria-allowed-attr',
    'aria-command-name',
    'aria-hidden-body',
    'aria-hidden-focus',
    'aria-input-field-name',
    'aria-meter-name',
    'aria-progressbar-name',
    'aria-required-attr',
    'aria-required-children',
    'aria-required-parent',
    'aria-roles',
    'aria-toggle-field-name',
    'aria-tooltip-name',
    'aria-valid-attr-value',
    'aria-valid-attr',
    'button-name',
    'bypass',
    'color-contrast',
    'definition-list',
    'dlitem',
    'document-title',
    'duplicate-id-active',
    'duplicate-id-aria',
    'form-field-multiple-labels',
    'frame-title',
    'heading-order',
    'html-has-lang',
    'html-lang-valid',
    'image-alt',
    'input-image-alt',
    'label',
    'landmark-one-main',
    'link-name',
    'list',
    'listitem',
    'meta-refresh',
    'meta-viewport',
    'object-alt',
    'tabindex',
    'td-headers-attr',
    'th-has-data-cells',
    'valid-lang',
    'video-caption'
  ],
  
  categories: {
    performance: {
      title: 'Performance',
      auditRefs: [
        // Core Web Vitals (weighted heavily)
        { id: 'first-contentful-paint', weight: 10, group: 'metrics' },
        { id: 'largest-contentful-paint', weight: 25, group: 'metrics' },
        { id: 'cumulative-layout-shift', weight: 25, group: 'metrics' },
        { id: 'total-blocking-time', weight: 30, group: 'metrics' },
        { id: 'speed-index', weight: 10, group: 'metrics' },
        
        // Optimization opportunities
        { id: 'unused-javascript', weight: 0, group: 'load-opportunities' },
        { id: 'unused-css-rules', weight: 0, group: 'load-opportunities' },
        { id: 'unminified-css', weight: 0, group: 'load-opportunities' },
        { id: 'unminified-javascript', weight: 0, group: 'load-opportunities' },
        { id: 'modern-image-formats', weight: 0, group: 'load-opportunities' },
        { id: 'uses-optimized-images', weight: 0, group: 'load-opportunities' },
        { id: 'uses-webp-images', weight: 0, group: 'load-opportunities' },
        { id: 'uses-text-compression', weight: 0, group: 'load-opportunities' },
        { id: 'uses-responsive-images', weight: 0, group: 'load-opportunities' },
        { id: 'render-blocking-resources', weight: 0, group: 'load-opportunities' },
        
        // Diagnostics
        { id: 'mainthread-work-breakdown', weight: 0, group: 'diagnostics' },
        { id: 'bootup-time', weight: 0, group: 'diagnostics' },
        { id: 'uses-rel-preload', weight: 0, group: 'diagnostics' },
        { id: 'uses-rel-preconnect', weight: 0, group: 'diagnostics' },
        { id: 'font-display', weight: 0, group: 'diagnostics' },
        { id: 'dom-size', weight: 0, group: 'diagnostics' },
        { id: 'critical-request-chains', weight: 0, group: 'diagnostics' },
        { id: 'user-timings', weight: 0, group: 'diagnostics' },
        { id: 'redirects', weight: 0, group: 'diagnostics' }
      ]
    }
  },
  
  groups: {
    'metrics': {
      title: 'Metrics'
    },
    'load-opportunities': {
      title: 'Opportunities',
      description: 'These suggestions can help your page load faster.'
    },
    'diagnostics': {
      title: 'Diagnostics',
      description: 'More information about the performance of your application.'
    }
  }
}