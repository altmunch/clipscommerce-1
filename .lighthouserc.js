module.exports = {
  ci: {
    collect: {
      url: ['http://localhost:3000'],
      numberOfRuns: 3,
      settings: {
        chromeFlags: '--no-sandbox --headless',
        preset: 'desktop',
        throttling: {
          rttMs: 40,
          throughputKbps: 10240,
          cpuSlowdownMultiplier: 1,
          requestLatencyMs: 0,
          downloadThroughputKbps: 0,
          uploadThroughputKbps: 0
        }
      }
    },
    assert: {
      assertions: {
        'categories:performance': ['error', { minScore: 0.8 }],
        'categories:accessibility': ['error', { minScore: 0.9 }],
        'categories:best-practices': ['error', { minScore: 0.9 }],
        'categories:seo': ['error', { minScore: 0.8 }],
        
        // Core Web Vitals
        'first-contentful-paint': ['error', { maxNumericValue: 1800 }],
        'largest-contentful-paint': ['error', { maxNumericValue: 2500 }],
        'cumulative-layout-shift': ['error', { maxNumericValue: 0.1 }],
        'total-blocking-time': ['error', { maxNumericValue: 300 }],
        'speed-index': ['error', { maxNumericValue: 3400 }],
        
        // Resource optimization
        'unused-javascript': ['warn', { maxNumericValue: 20000 }],
        'unused-css-rules': ['warn', { maxNumericValue: 20000 }],
        'modern-image-formats': ['warn', { maxNumericValue: 85 }],
        'uses-optimized-images': ['warn', { maxNumericValue: 85 }],
        'uses-webp-images': ['warn', { maxNumericValue: 85 }],
        'uses-text-compression': ['error', { maxNumericValue: 85 }],
        'uses-responsive-images': ['warn', { maxNumericValue: 85 }],
        'render-blocking-resources': ['warn', { maxNumericValue: 500 }],
        
        // Performance budgets
        'total-byte-weight': ['error', { maxNumericValue: 3000000 }], // 3MB
        'dom-size': ['warn', { maxNumericValue: 1500 }],
        'bootup-time': ['warn', { maxNumericValue: 4000 }],
        'mainthread-work-breakdown': ['warn', { maxNumericValue: 4000 }]
      }
    },
    upload: {
      target: 'temporary-public-storage'
    },
    server: {
      port: 9001,
      storage: '.lighthouseci'
    }
  }
}