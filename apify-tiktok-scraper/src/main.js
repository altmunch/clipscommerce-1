/**
 * ViralOS TikTok Trend Scraper
 * 
 * Advanced TikTok scraper for extracting trending content, hashtags, sounds,
 * and viral patterns with comprehensive analytics and pattern recognition.
 * 
 * Features:
 * - Multi-mode scraping (trending, hashtag, sound, user, discover)
 * - Anti-bot evasion with stealth techniques
 * - Intelligent rate limiting and retry logic
 * - Comprehensive trend analysis and pattern recognition
 * - Geographic and demographic data extraction
 * - Sound and effect tracking
 * - Video structure and hook analysis
 */

const Apify = require('apify');
const { chromium } = require('playwright-extra');
const StealthPlugin = require('playwright-extra-plugin-stealth');
const UserAgent = require('user-agents');
const cheerio = require('cheerio');
const _ = require('lodash');
const moment = require('moment');
const pLimit = require('p-limit');
const pRetry = require('p-retry');

// Add stealth plugin
chromium.use(StealthPlugin());

// Rate limiting
const concurrencyLimit = pLimit(3); // Limit concurrent requests
const pageLimit = pLimit(1); // Limit concurrent pages

/**
 * TikTok Trend Scraper Class
 */
class TikTokTrendScraper {
    constructor(input, requestQueue, proxyConfiguration) {
        this.input = input;
        this.requestQueue = requestQueue;
        this.proxyConfiguration = proxyConfiguration;
        
        // Scraping configuration
        this.maxRetries = 3;
        this.retryDelay = 2000;
        this.requestDelay = 1000;
        
        // Data storage
        this.scrapedVideos = new Map();
        this.trendData = new Map();
        this.hashtagData = new Map();
        this.soundData = new Map();
        
        // Analytics
        this.stats = {
            videosProcessed: 0,
            trendsIdentified: 0,
            hashtagsDiscovered: 0,
            soundsTracked: 0,
            errors: 0,
            startTime: Date.now()
        };
    }

    /**
     * Initialize browser and context
     */
    async initializeBrowser() {
        console.log('🚀 Initializing browser...');
        
        const userAgent = new UserAgent({ deviceCategory: 'desktop' });
        
        const browserOptions = {
            headless: true,
            args: [
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--no-first-run',
                '--no-zygote',
                '--disable-gpu',
                '--disable-background-timer-throttling',
                '--disable-backgrounding-occluded-windows',
                '--disable-renderer-backgrounding'
            ]
        };

        // Add proxy if configured
        if (this.proxyConfiguration) {
            const proxyUrl = await this.proxyConfiguration.newUrl();
            if (proxyUrl) {
                const url = new URL(proxyUrl);
                browserOptions.proxy = {
                    server: `${url.protocol}//${url.host}`,
                    username: url.username,
                    password: url.password
                };
            }
        }

        this.browser = await chromium.launch(browserOptions);
        
        this.context = await this.browser.newContext({
            userAgent: userAgent.toString(),
            viewport: { width: 1920, height: 1080 },
            locale: 'en-US',
            timezoneId: 'America/New_York',
            permissions: ['geolocation'],
            geolocation: { latitude: 40.7128, longitude: -74.0060 }, // NYC
            deviceScaleFactor: 1,
            isMobile: false
        });

        // Block unnecessary resources to speed up scraping
        await this.context.route('**/*', (route) => {
            const resourceType = route.request().resourceType();
            if (['image', 'stylesheet', 'font', 'media'].includes(resourceType)) {
                route.abort();
            } else {
                route.continue();
            }
        });
    }

    /**
     * Main scraping orchestrator
     */
    async scrape() {
        console.log(`📊 Starting TikTok scraping in ${this.input.mode} mode...`);
        
        await this.initializeBrowser();
        
        try {
            switch (this.input.mode) {
                case 'trending':
                    await this.scrapeTrendingContent();
                    break;
                case 'hashtag':
                    await this.scrapeHashtagContent();
                    break;
                case 'sound':
                    await this.scrapeSoundContent();
                    break;
                case 'user':
                    await this.scrapeUserContent();
                    break;
                case 'discover':
                    await this.scrapeDiscoverContent();
                    break;
                default:
                    throw new Error(`Unknown scraping mode: ${this.input.mode}`);
            }

            // Perform trend analysis if enabled
            if (this.input.includeTrendAnalysis) {
                await this.analyzeTrends();
            }

            // Generate final analytics
            await this.generateAnalytics();

        } finally {
            await this.cleanup();
        }
    }

    /**
     * Scrape trending content from TikTok
     */
    async scrapeTrendingContent() {
        console.log('🔥 Scraping trending content...');
        
        const page = await this.context.newPage();
        
        try {
            // Navigate to TikTok trending/discover page
            await this.navigateToTikTok(page, 'https://www.tiktok.com/foryou');
            
            // Wait for content to load
            await this.waitForContent(page);
            
            let videosScraped = 0;
            let scrollAttempts = 0;
            const maxScrolls = Math.ceil(this.input.maxVideos / 10); // Estimate videos per scroll
            
            while (videosScraped < this.input.maxVideos && scrollAttempts < maxScrolls) {
                // Extract videos from current view
                const videos = await this.extractVideosFromPage(page);
                
                // Process each video
                for (const video of videos) {
                    if (videosScraped >= this.input.maxVideos) break;
                    
                    try {
                        const processedVideo = await this.processVideo(video, page);
                        if (processedVideo) {
                            await this.saveVideo(processedVideo);
                            videosScraped++;
                            this.stats.videosProcessed++;
                        }
                    } catch (error) {
                        console.log(`❌ Error processing video: ${error.message}`);
                        this.stats.errors++;
                    }
                    
                    // Rate limiting
                    await this.delay(this.requestDelay);
                }
                
                // Scroll to load more content
                await this.scrollPage(page);
                scrollAttempts++;
                
                // Random delay between scrolls
                await this.delay(_.random(2000, 4000));
            }
            
        } finally {
            await page.close();
        }
        
        console.log(`✅ Scraped ${videosScraped} trending videos`);
    }

    /**
     * Scrape content for specific hashtags
     */
    async scrapeHashtagContent() {
        console.log('🏷️ Scraping hashtag content...');
        
        if (!this.input.targets || this.input.targets.length === 0) {
            throw new Error('No hashtags specified for hashtag mode');
        }
        
        for (const hashtag of this.input.targets) {
            await this.scrapeHashtagVideos(hashtag);
        }
    }

    /**
     * Scrape videos for a specific hashtag
     */
    async scrapeHashtagVideos(hashtag) {
        console.log(`🎯 Scraping hashtag: ${hashtag}`);
        
        const page = await this.context.newPage();
        
        try {
            const cleanHashtag = hashtag.replace('#', '');
            const url = `https://www.tiktok.com/tag/${encodeURIComponent(cleanHashtag)}`;
            
            await this.navigateToTikTok(page, url);
            await this.waitForContent(page);
            
            // Extract hashtag metrics
            const hashtagMetrics = await this.extractHashtagMetrics(page, hashtag);
            await this.saveHashtagData(hashtagMetrics);
            
            // Scrape videos under this hashtag
            let videosScraped = 0;
            let scrollAttempts = 0;
            const maxVideosPerHashtag = Math.floor(this.input.maxVideos / this.input.targets.length);
            
            while (videosScraped < maxVideosPerHashtag && scrollAttempts < 20) {
                const videos = await this.extractVideosFromPage(page);
                
                for (const video of videos) {
                    if (videosScraped >= maxVideosPerHashtag) break;
                    
                    try {
                        const processedVideo = await this.processVideo(video, page);
                        if (processedVideo) {
                            processedVideo.sourceHashtag = hashtag;
                            await this.saveVideo(processedVideo);
                            videosScraped++;
                            this.stats.videosProcessed++;
                        }
                    } catch (error) {
                        console.log(`❌ Error processing video: ${error.message}`);
                        this.stats.errors++;
                    }
                    
                    await this.delay(this.requestDelay);
                }
                
                await this.scrollPage(page);
                scrollAttempts++;
                await this.delay(_.random(2000, 4000));
            }
            
        } finally {
            await page.close();
        }
        
        console.log(`✅ Scraped ${this.stats.videosProcessed} videos for hashtag: ${hashtag}`);
    }

    /**
     * Scrape sound/music content
     */
    async scrapeSoundContent() {
        console.log('🎵 Scraping sound content...');
        
        if (!this.input.targets || this.input.targets.length === 0) {
            throw new Error('No sounds specified for sound mode');
        }
        
        for (const soundId of this.input.targets) {
            await this.scrapeSoundVideos(soundId);
        }
    }

    /**
     * Scrape videos for a specific sound
     */
    async scrapeSoundVideos(soundId) {
        console.log(`🎼 Scraping sound: ${soundId}`);
        
        const page = await this.context.newPage();
        
        try {
            const url = `https://www.tiktok.com/music/${encodeURIComponent(soundId)}`;
            
            await this.navigateToTikTok(page, url);
            await this.waitForContent(page);
            
            // Extract sound metrics
            const soundMetrics = await this.extractSoundMetrics(page, soundId);
            await this.saveSoundData(soundMetrics);
            
            // Scrape videos using this sound
            let videosScraped = 0;
            let scrollAttempts = 0;
            const maxVideosPerSound = Math.floor(this.input.maxVideos / this.input.targets.length);
            
            while (videosScraped < maxVideosPerSound && scrollAttempts < 20) {
                const videos = await this.extractVideosFromPage(page);
                
                for (const video of videos) {
                    if (videosScraped >= maxVideosPerSound) break;
                    
                    try {
                        const processedVideo = await this.processVideo(video, page);
                        if (processedVideo) {
                            processedVideo.sourceSound = soundId;
                            await this.saveVideo(processedVideo);
                            videosScraped++;
                            this.stats.videosProcessed++;
                        }
                    } catch (error) {
                        console.log(`❌ Error processing video: ${error.message}`);
                        this.stats.errors++;
                    }
                    
                    await this.delay(this.requestDelay);
                }
                
                await this.scrollPage(page);
                scrollAttempts++;
                await this.delay(_.random(2000, 4000));
            }
            
        } finally {
            await page.close();
        }
    }

    /**
     * Scrape user content
     */
    async scrapeUserContent() {
        console.log('👤 Scraping user content...');
        
        if (!this.input.targets || this.input.targets.length === 0) {
            throw new Error('No users specified for user mode');
        }
        
        for (const username of this.input.targets) {
            await this.scrapeUserVideos(username);
        }
    }

    /**
     * Scrape videos from a specific user
     */
    async scrapeUserVideos(username) {
        console.log(`👨‍💼 Scraping user: ${username}`);
        
        const page = await this.context.newPage();
        
        try {
            const cleanUsername = username.replace('@', '');
            const url = `https://www.tiktok.com/@${encodeURIComponent(cleanUsername)}`;
            
            await this.navigateToTikTok(page, url);
            await this.waitForContent(page);
            
            // Extract user metrics
            const userMetrics = await this.extractUserMetrics(page, username);
            
            // Scrape user's videos
            let videosScraped = 0;
            let scrollAttempts = 0;
            const maxVideosPerUser = Math.floor(this.input.maxVideos / this.input.targets.length);
            
            while (videosScraped < maxVideosPerUser && scrollAttempts < 20) {
                const videos = await this.extractVideosFromPage(page);
                
                for (const video of videos) {
                    if (videosScraped >= maxVideosPerUser) break;
                    
                    try {
                        const processedVideo = await this.processVideo(video, page);
                        if (processedVideo) {
                            processedVideo.sourceUser = username;
                            processedVideo.userMetrics = userMetrics;
                            await this.saveVideo(processedVideo);
                            videosScraped++;
                            this.stats.videosProcessed++;
                        }
                    } catch (error) {
                        console.log(`❌ Error processing video: ${error.message}`);
                        this.stats.errors++;
                    }
                    
                    await this.delay(this.requestDelay);
                }
                
                await this.scrollPage(page);
                scrollAttempts++;
                await this.delay(_.random(2000, 4000));
            }
            
        } finally {
            await page.close();
        }
    }

    /**
     * Scrape discover content
     */
    async scrapeDiscoverContent() {
        console.log('🔍 Scraping discover content...');
        
        const page = await this.context.newPage();
        
        try {
            await this.navigateToTikTok(page, 'https://www.tiktok.com/discover');
            await this.waitForContent(page);
            
            // Extract trending hashtags and sounds from discover page
            const discoverData = await this.extractDiscoverData(page);
            
            // Process discovered trends
            for (const trend of discoverData.trends) {
                await this.saveTrendData(trend);
            }
            
            for (const hashtag of discoverData.hashtags) {
                await this.saveHashtagData(hashtag);
            }
            
            for (const sound of discoverData.sounds) {
                await this.saveSoundData(sound);
            }
            
        } finally {
            await page.close();
        }
    }

    /**
     * Navigate to TikTok with stealth measures
     */
    async navigateToTikTok(page, url) {
        console.log(`🌐 Navigating to: ${url}`);
        
        // Set additional headers
        await page.setExtraHTTPHeaders({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        });

        // Navigate with retry logic
        await pRetry(async () => {
            const response = await page.goto(url, {
                waitUntil: 'networkidle',
                timeout: 30000
            });
            
            if (!response.ok()) {
                throw new Error(`Navigation failed with status: ${response.status()}`);
            }
            
            return response;
        }, {
            retries: this.maxRetries,
            minTimeout: this.retryDelay,
            maxTimeout: this.retryDelay * 3
        });

        // Random human-like delay
        await this.delay(_.random(1000, 3000));
    }

    /**
     * Wait for content to load
     */
    async waitForContent(page) {
        try {
            // Wait for video containers to load
            await page.waitForSelector('[data-e2e="recommend-list-item"]', { timeout: 10000 });
        } catch (error) {
            console.log('⚠️ Standard video selector not found, trying alternatives...');
            
            // Try alternative selectors
            const selectors = [
                'div[data-e2e="recommend-list-item"]',
                'div[class*="DivItemContainer"]',
                'div[class*="video-feed-item"]',
                'div[class*="video-card"]'
            ];
            
            for (const selector of selectors) {
                try {
                    await page.waitForSelector(selector, { timeout: 5000 });
                    console.log(`✅ Found content with selector: ${selector}`);
                    return;
                } catch (e) {
                    continue;
                }
            }
            
            console.log('⚠️ Could not find video content selectors');
        }
    }

    /**
     * Extract videos from current page view
     */
    async extractVideosFromPage(page) {
        console.log('📹 Extracting videos from page...');
        
        const videos = await page.evaluate(() => {
            const videoElements = [];
            
            // Multiple selector strategies for video containers
            const selectors = [
                '[data-e2e="recommend-list-item"]',
                'div[class*="DivItemContainer"]',
                'div[class*="video-feed-item"]',
                'div[class*="video-card"]'
            ];
            
            let foundElements = [];
            
            for (const selector of selectors) {
                const elements = document.querySelectorAll(selector);
                if (elements.length > 0) {
                    foundElements = Array.from(elements);
                    break;
                }
            }
            
            foundElements.forEach((element, index) => {
                try {
                    const video = {
                        index,
                        id: null,
                        url: null,
                        description: null,
                        hashtags: [],
                        mentions: [],
                        sounds: [],
                        stats: {
                            views: 0,
                            likes: 0,
                            shares: 0,
                            comments: 0
                        },
                        creator: {
                            username: null,
                            displayName: null,
                            verified: false
                        },
                        timestamp: null,
                        duration: null,
                        rawElement: element.outerHTML.substring(0, 1000) // Truncated for debugging
                    };
                    
                    // Extract video ID and URL
                    const linkElement = element.querySelector('a[href*="/video/"]');
                    if (linkElement) {
                        video.url = linkElement.href;
                        const urlMatch = video.url.match(/\/video\/(\d+)/);
                        if (urlMatch) {
                            video.id = urlMatch[1];
                        }
                    }
                    
                    // Extract description
                    const descSelectors = [
                        '[data-e2e="video-desc"]',
                        'div[class*="video-meta-caption"]',
                        'div[class*="tt-video-meta-caption"]'
                    ];
                    
                    for (const selector of descSelectors) {
                        const descElement = element.querySelector(selector);
                        if (descElement) {
                            video.description = descElement.textContent.trim();
                            break;
                        }
                    }
                    
                    // Extract hashtags and mentions from description
                    if (video.description) {
                        video.hashtags = (video.description.match(/#\\w+/g) || []).map(tag => tag.toLowerCase());
                        video.mentions = (video.description.match(/@\\w+/g) || []).map(mention => mention.toLowerCase());
                    }
                    
                    // Extract creator info
                    const creatorSelectors = [
                        '[data-e2e="video-author"]',
                        'span[class*="author-uniqueid"]',
                        'a[class*="author-link"]'
                    ];
                    
                    for (const selector of creatorSelectors) {
                        const creatorElement = element.querySelector(selector);
                        if (creatorElement) {
                            video.creator.username = creatorElement.textContent.trim().replace('@', '');
                            break;
                        }
                    }
                    
                    // Extract engagement stats
                    const statSelectors = {
                        likes: ['[data-e2e="like-count"]', 'strong[title*="like"]'],
                        comments: ['[data-e2e="comment-count"]', 'strong[title*="comment"]'],
                        shares: ['[data-e2e="share-count"]', 'strong[title*="share"]'],
                        views: ['[data-e2e="video-views"]', 'strong[title*="view"]']
                    };
                    
                    Object.keys(statSelectors).forEach(stat => {
                        for (const selector of statSelectors[stat]) {
                            const statElement = element.querySelector(selector);
                            if (statElement) {
                                const text = statElement.textContent.trim();
                                video.stats[stat] = this.parseEngagementNumber(text);
                                break;
                            }
                        }
                    });
                    
                    // Only include videos with valid IDs
                    if (video.id) {
                        videoElements.push(video);
                    }
                    
                } catch (error) {
                    console.log(`Error extracting video ${index}:`, error.message);
                }
            });
            
            return videoElements;
        });
        
        console.log(`📊 Extracted ${videos.length} videos from page`);
        return videos;
    }

    /**
     * Process individual video with detailed analysis
     */
    async processVideo(video, page) {
        if (!video.id || this.scrapedVideos.has(video.id)) {
            return null; // Skip duplicates
        }
        
        console.log(`🎬 Processing video: ${video.id}`);
        
        try {
            // Enhanced video data
            const processedVideo = {
                ...video,
                scrapedAt: new Date().toISOString(),
                processingVersion: '1.0.0',
                engagementRate: 0,
                viralScore: 0,
                contentAnalysis: {},
                trendIndicators: [],
                timestamp: new Date().toISOString()
            };
            
            // Calculate engagement metrics
            if (this.input.includeEngagementMetrics) {
                processedVideo.engagementRate = this.calculateEngagementRate(processedVideo.stats);
                processedVideo.viralScore = this.calculateViralScore(processedVideo);
            }
            
            // Perform video content analysis
            if (this.input.includeVideoAnalysis) {
                processedVideo.contentAnalysis = await this.analyzeVideoContent(processedVideo, page);
            }
            
            // Filter by minimum engagement
            if (processedVideo.stats.likes + processedVideo.stats.comments + processedVideo.stats.shares < this.input.minEngagement) {
                return null;
            }
            
            this.scrapedVideos.set(video.id, processedVideo);
            return processedVideo;
            
        } catch (error) {
            console.log(`❌ Error processing video ${video.id}: ${error.message}`);
            this.stats.errors++;
            return null;
        }
    }

    /**
     * Analyze video content for hooks, structure, and patterns
     */
    async analyzeVideoContent(video, page) {
        const analysis = {
            hooks: [],
            structure: {},
            visualElements: [],
            audioFeatures: {},
            trends: []
        };
        
        try {
            // Analyze description for hooks and patterns
            if (video.description) {
                analysis.hooks = this.extractContentHooks(video.description);
                analysis.trends = this.identifyTrendPatterns(video.description);
            }
            
            // Analyze hashtag patterns
            if (video.hashtags.length > 0) {
                analysis.hashtagStrategy = this.analyzeHashtagStrategy(video.hashtags);
            }
            
            // Analyze viral indicators
            analysis.viralIndicators = this.identifyViralIndicators(video);
            
        } catch (error) {
            console.log(`⚠️ Content analysis error: ${error.message}`);
        }
        
        return analysis;
    }

    /**
     * Extract content hooks from video description
     */
    extractContentHooks(description) {
        const hooks = [];
        
        const hookPatterns = [
            /^(POV|POV:|When|If you|Imagine|What if|Did you know|Fun fact)/i,
            /\\?(\\w+\\s+){1,3}\\?/g, // Questions
            /(This|That|Here's how|Watch this|Check this)/i,
            /(You won't believe|Wait for it|Plot twist)/i
        ];
        
        hookPatterns.forEach(pattern => {
            const matches = description.match(pattern);
            if (matches) {
                hooks.push(...matches);
            }
        });
        
        return hooks.map(hook => hook.trim()).slice(0, 5);
    }

    /**
     * Identify trend patterns in content
     */
    identifyTrendPatterns(description) {
        const patterns = [];
        
        const trendKeywords = [
            'challenge', 'trend', 'viral', 'fyp', 'trending',
            'dance', 'tutorial', 'hack', 'tips', 'diy',
            'transformation', 'before and after', 'storytime'
        ];
        
        trendKeywords.forEach(keyword => {
            if (description.toLowerCase().includes(keyword)) {
                patterns.push(keyword);
            }
        });
        
        return patterns;
    }

    /**
     * Analyze hashtag strategy
     */
    analyzeHashtagStrategy(hashtags) {
        return {
            totalHashtags: hashtags.length,
            trendingHashtags: hashtags.filter(tag => this.isTrendingHashtag(tag)),
            nicheHashtags: hashtags.filter(tag => !this.isTrendingHashtag(tag)),
            strategy: hashtags.length > 10 ? 'mass' : hashtags.length > 5 ? 'balanced' : 'minimal'
        };
    }

    /**
     * Check if hashtag is trending
     */
    isTrendingHashtag(hashtag) {
        const trendingHashtags = [
            '#fyp', '#foryou', '#viral', '#trending', '#tiktok',
            '#xyzbca', '#foryoupage', '#viral', '#trend'
        ];
        
        return trendingHashtags.includes(hashtag.toLowerCase());
    }

    /**
     * Identify viral indicators
     */
    identifyViralIndicators(video) {
        const indicators = [];
        
        // High engagement rate
        if (video.engagementRate > 5) {
            indicators.push('high_engagement');
        }
        
        // High like-to-view ratio
        const likeRatio = video.stats.views > 0 ? (video.stats.likes / video.stats.views) * 100 : 0;
        if (likeRatio > 3) {
            indicators.push('high_like_ratio');
        }
        
        // High share count relative to likes
        const shareRatio = video.stats.likes > 0 ? (video.stats.shares / video.stats.likes) * 100 : 0;
        if (shareRatio > 10) {
            indicators.push('highly_shareable');
        }
        
        // Uses trending hashtags
        if (video.hashtags.some(tag => this.isTrendingHashtag(tag))) {
            indicators.push('trending_hashtags');
        }
        
        return indicators;
    }

    /**
     * Calculate engagement rate
     */
    calculateEngagementRate(stats) {
        if (stats.views === 0) return 0;
        
        const totalEngagement = stats.likes + stats.comments + stats.shares;
        return (totalEngagement / stats.views) * 100;
    }

    /**
     * Calculate viral score
     */
    calculateViralScore(video) {
        let score = 0;
        
        // Engagement rate factor (0-40 points)
        score += Math.min(video.engagementRate * 8, 40);
        
        // View count factor (0-20 points)
        if (video.stats.views > 1000000) score += 20;
        else if (video.stats.views > 100000) score += 15;
        else if (video.stats.views > 10000) score += 10;
        else if (video.stats.views > 1000) score += 5;
        
        // Hashtag strategy (0-15 points)
        if (video.hashtags.length > 0) {
            const trendingCount = video.hashtags.filter(tag => this.isTrendingHashtag(tag)).length;
            score += Math.min(trendingCount * 3, 15);
        }
        
        // Content hooks (0-15 points)
        if (video.contentAnalysis && video.contentAnalysis.hooks) {
            score += Math.min(video.contentAnalysis.hooks.length * 3, 15);
        }
        
        // Share factor (0-10 points)
        const shareRatio = video.stats.likes > 0 ? (video.stats.shares / video.stats.likes) * 100 : 0;
        score += Math.min(shareRatio, 10);
        
        return Math.min(Math.round(score), 100);
    }

    /**
     * Extract hashtag metrics
     */
    async extractHashtagMetrics(page, hashtag) {
        console.log(`📊 Extracting metrics for hashtag: ${hashtag}`);
        
        const metrics = {
            hashtag: hashtag,
            totalViews: 0,
            totalVideos: 0,
            isOfficial: false,
            relatedHashtags: [],
            topCreators: [],
            scrapedAt: new Date().toISOString()
        };
        
        try {
            // Extract view count
            const viewElements = await page.$$('[class*="view"]');
            for (const element of viewElements) {
                const text = await element.textContent();
                if (text && text.includes('view')) {
                    metrics.totalViews = this.parseEngagementNumber(text);
                    break;
                }
            }
            
            // Extract related hashtags
            const hashtagElements = await page.$$('a[href*="/tag/"]');
            for (const element of hashtagElements.slice(0, 10)) {
                const href = await element.getAttribute('href');
                const tag = href.match(/\\/tag\\/([^/?]+)/);
                if (tag && tag[1] !== hashtag.replace('#', '')) {
                    metrics.relatedHashtags.push('#' + tag[1]);
                }
            }
            
        } catch (error) {
            console.log(`⚠️ Error extracting hashtag metrics: ${error.message}`);
        }
        
        return metrics;
    }

    /**
     * Extract sound metrics
     */
    async extractSoundMetrics(page, soundId) {
        console.log(`🎵 Extracting metrics for sound: ${soundId}`);
        
        const metrics = {
            soundId: soundId,
            title: null,
            artist: null,
            totalVideos: 0,
            isOriginal: false,
            duration: null,
            topCreators: [],
            scrapedAt: new Date().toISOString()
        };
        
        try {
            // Extract sound title
            const titleElement = await page.$('[class*="sound-title"], [class*="music-title"]');
            if (titleElement) {
                metrics.title = await titleElement.textContent();
            }
            
            // Extract artist name
            const artistElement = await page.$('[class*="sound-artist"], [class*="music-artist"]');
            if (artistElement) {
                metrics.artist = await artistElement.textContent();
            }
            
            // Extract video count
            const countElements = await page.$$('[class*="count"], [class*="video"]');
            for (const element of countElements) {
                const text = await element.textContent();
                if (text && text.includes('video')) {
                    metrics.totalVideos = this.parseEngagementNumber(text);
                    break;
                }
            }
            
        } catch (error) {
            console.log(`⚠️ Error extracting sound metrics: ${error.message}`);
        }
        
        return metrics;
    }

    /**
     * Extract user metrics
     */
    async extractUserMetrics(page, username) {
        console.log(`👤 Extracting metrics for user: ${username}`);
        
        const metrics = {
            username: username,
            displayName: null,
            followers: 0,
            following: 0,
            likes: 0,
            videos: 0,
            verified: false,
            scrapedAt: new Date().toISOString()
        };
        
        try {
            // Extract display name
            const nameElement = await page.$('[data-e2e="user-title"]');
            if (nameElement) {
                metrics.displayName = await nameElement.textContent();
            }
            
            // Extract follower count
            const followerElement = await page.$('[data-e2e="followers-count"]');
            if (followerElement) {
                const text = await followerElement.textContent();
                metrics.followers = this.parseEngagementNumber(text);
            }
            
            // Extract following count
            const followingElement = await page.$('[data-e2e="following-count"]');
            if (followingElement) {
                const text = await followingElement.textContent();
                metrics.following = this.parseEngagementNumber(text);
            }
            
            // Check if verified
            const verifiedElement = await page.$('[data-e2e="user-verified"]');
            metrics.verified = !!verifiedElement;
            
        } catch (error) {
            console.log(`⚠️ Error extracting user metrics: ${error.message}`);
        }
        
        return metrics;
    }

    /**
     * Extract discover page data
     */
    async extractDiscoverData(page) {
        console.log('🔍 Extracting discover page data...');
        
        const discoverData = {
            trends: [],
            hashtags: [],
            sounds: [],
            challenges: [],
            scrapedAt: new Date().toISOString()
        };
        
        try {
            // Extract trending hashtags
            const hashtagElements = await page.$$('a[href*="/tag/"]');
            for (const element of hashtagElements.slice(0, 20)) {
                const href = await element.getAttribute('href');
                const text = await element.textContent();
                const tag = href.match(/\\/tag\\/([^/?]+)/);
                
                if (tag) {
                    discoverData.hashtags.push({
                        hashtag: '#' + tag[1],
                        displayText: text,
                        url: href
                    });
                }
            }
            
            // Extract trending sounds
            const soundElements = await page.$$('a[href*="/music/"]');
            for (const element of soundElements.slice(0, 10)) {
                const href = await element.getAttribute('href');
                const text = await element.textContent();
                const soundId = href.match(/\\/music\\/([^/?]+)/);
                
                if (soundId) {
                    discoverData.sounds.push({
                        soundId: soundId[1],
                        title: text,
                        url: href
                    });
                }
            }
            
        } catch (error) {
            console.log(`⚠️ Error extracting discover data: ${error.message}`);
        }
        
        return discoverData;
    }

    /**
     * Parse engagement numbers (handles K, M, B suffixes)
     */
    parseEngagementNumber(text) {
        if (!text) return 0;
        
        const cleanText = text.replace(/[^0-9.KMB]/gi, '');
        const number = parseFloat(cleanText);
        
        if (isNaN(number)) return 0;
        
        if (cleanText.includes('B')) return Math.round(number * 1000000000);
        if (cleanText.includes('M')) return Math.round(number * 1000000);
        if (cleanText.includes('K')) return Math.round(number * 1000);
        
        return Math.round(number);
    }

    /**
     * Scroll page to load more content
     */
    async scrollPage(page) {
        await page.evaluate(() => {
            window.scrollBy(0, window.innerHeight * 2);
        });
        
        // Wait for new content to load
        await this.delay(2000);
    }

    /**
     * Perform trend analysis on collected data
     */
    async analyzeTrends() {
        console.log('📈 Analyzing trends...');
        
        const videos = Array.from(this.scrapedVideos.values());
        
        // Analyze hashtag trends
        const hashtagAnalysis = this.analyzeHashtagTrends(videos);
        
        // Analyze sound trends
        const soundAnalysis = this.analyzeSoundTrends(videos);
        
        // Analyze content patterns
        const contentAnalysis = this.analyzeContentPatterns(videos);
        
        // Save trend analysis results
        await this.saveTrendAnalysis({
            hashtags: hashtagAnalysis,
            sounds: soundAnalysis,
            content: contentAnalysis,
            analyzedAt: new Date().toISOString()
        });
    }

    /**
     * Analyze hashtag trends
     */
    analyzeHashtagTrends(videos) {
        const hashtagStats = new Map();
        
        videos.forEach(video => {
            video.hashtags.forEach(hashtag => {
                if (!hashtagStats.has(hashtag)) {
                    hashtagStats.set(hashtag, {
                        hashtag,
                        count: 0,
                        totalViews: 0,
                        totalLikes: 0,
                        avgEngagement: 0,
                        videos: []
                    });
                }
                
                const stats = hashtagStats.get(hashtag);
                stats.count++;
                stats.totalViews += video.stats.views;
                stats.totalLikes += video.stats.likes;
                stats.videos.push(video.id);
            });
        });
        
        // Calculate averages and sort by popularity
        const analysis = Array.from(hashtagStats.values()).map(stats => {
            stats.avgEngagement = stats.count > 0 ? (stats.totalLikes / stats.totalViews) * 100 : 0;
            return stats;
        }).sort((a, b) => b.count - a.count);
        
        return analysis.slice(0, 50); // Top 50 hashtags
    }

    /**
     * Analyze sound trends
     */
    analyzeSoundTrends(videos) {
        const soundStats = new Map();
        
        videos.forEach(video => {
            video.sounds.forEach(sound => {
                if (!soundStats.has(sound)) {
                    soundStats.set(sound, {
                        sound,
                        count: 0,
                        totalViews: 0,
                        totalLikes: 0,
                        videos: []
                    });
                }
                
                const stats = soundStats.get(sound);
                stats.count++;
                stats.totalViews += video.stats.views;
                stats.totalLikes += video.stats.likes;
                stats.videos.push(video.id);
            });
        });
        
        return Array.from(soundStats.values()).sort((a, b) => b.count - a.count).slice(0, 30);
    }

    /**
     * Analyze content patterns
     */
    analyzeContentPatterns(videos) {
        const patterns = {
            commonHooks: {},
            viralFormats: {},
            engagementPatterns: {},
            timingPatterns: {}
        };
        
        videos.forEach(video => {
            // Analyze hooks
            if (video.contentAnalysis && video.contentAnalysis.hooks) {
                video.contentAnalysis.hooks.forEach(hook => {
                    patterns.commonHooks[hook] = (patterns.commonHooks[hook] || 0) + 1;
                });
            }
            
            // Analyze engagement patterns
            const engagementTier = this.categorizeEngagement(video.engagementRate);
            patterns.engagementPatterns[engagementTier] = (patterns.engagementPatterns[engagementTier] || 0) + 1;
        });
        
        return patterns;
    }

    /**
     * Categorize engagement level
     */
    categorizeEngagement(rate) {
        if (rate > 10) return 'extremely_high';
        if (rate > 5) return 'high';
        if (rate > 2) return 'medium';
        if (rate > 0.5) return 'low';
        return 'very_low';
    }

    /**
     * Generate analytics summary
     */
    async generateAnalytics() {
        console.log('📊 Generating analytics...');
        
        const duration = (Date.now() - this.stats.startTime) / 1000;
        this.stats.duration = duration;
        this.stats.videosPerSecond = this.stats.videosProcessed / duration;
        this.stats.successRate = this.stats.videosProcessed / (this.stats.videosProcessed + this.stats.errors);
        
        await Apify.setValue('ANALYTICS', this.stats);
        
        console.log('📈 Analytics Summary:');
        console.log(`   Videos Processed: ${this.stats.videosProcessed}`);
        console.log(`   Trends Identified: ${this.stats.trendsIdentified}`);
        console.log(`   Hashtags Discovered: ${this.stats.hashtagsDiscovered}`);
        console.log(`   Sounds Tracked: ${this.stats.soundsTracked}`);
        console.log(`   Errors: ${this.stats.errors}`);
        console.log(`   Duration: ${duration.toFixed(2)}s`);
        console.log(`   Success Rate: ${(this.stats.successRate * 100).toFixed(2)}%`);
    }

    /**
     * Save video data
     */
    async saveVideo(video) {
        await Apify.pushData(video);
    }

    /**
     * Save hashtag data
     */
    async saveHashtagData(hashtag) {
        this.hashtagData.set(hashtag.hashtag, hashtag);
        this.stats.hashtagsDiscovered++;
        await Apify.setValue(`HASHTAG_${hashtag.hashtag.replace('#', '')}`, hashtag);
    }

    /**
     * Save sound data
     */
    async saveSoundData(sound) {
        this.soundData.set(sound.soundId, sound);
        this.stats.soundsTracked++;
        await Apify.setValue(`SOUND_${sound.soundId}`, sound);
    }

    /**
     * Save trend data
     */
    async saveTrendData(trend) {
        this.trendData.set(trend.id || trend.name, trend);
        this.stats.trendsIdentified++;
        await Apify.setValue(`TREND_${trend.id || trend.name}`, trend);
    }

    /**
     * Save trend analysis
     */
    async saveTrendAnalysis(analysis) {
        await Apify.setValue('TREND_ANALYSIS', analysis);
    }

    /**
     * Utility delay function
     */
    async delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    /**
     * Cleanup resources
     */
    async cleanup() {
        console.log('🧹 Cleaning up...');
        
        if (this.context) {
            await this.context.close();
        }
        
        if (this.browser) {
            await this.browser.close();
        }
    }
}

/**
 * Main execution function
 */
Apify.main(async () => {
    console.log('🚀 Starting ViralOS TikTok Trend Scraper...');
    
    // Get input and configuration
    const input = await Apify.getInput();
    
    // Validate input
    if (!input || !input.mode) {
        throw new Error('Missing required input: mode');
    }
    
    // Initialize Apify components
    const requestQueue = await Apify.openRequestQueue();
    
    // Setup proxy configuration
    const proxyConfiguration = await Apify.createProxyConfiguration({
        useApifyProxy: input.proxyConfiguration?.useApifyProxy || true,
        apifyProxyGroups: input.proxyConfiguration?.apifyProxyGroups || ['RESIDENTIAL']
    });
    
    // Initialize scraper
    const scraper = new TikTokTrendScraper(input, requestQueue, proxyConfiguration);
    
    try {
        // Run scraping
        await scraper.scrape();
        
        console.log('✅ Scraping completed successfully!');
        
    } catch (error) {
        console.error('❌ Scraping failed:', error);
        throw error;
    }
});