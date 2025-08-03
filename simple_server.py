#!/usr/bin/env python3
"""
Simple standalone test server for ClipsCommerce Core Pipeline
This bypasses complex dependencies for quick testing
"""

import json
import time
import hashlib
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import threading

class CorePipelineHandler(BaseHTTPRequestHandler):
    """Simple HTTP handler for core pipeline testing"""
    
    def do_GET(self):
        """Handle GET requests"""
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            with open('test_interface.html', 'r') as f:
                self.wfile.write(f.read().encode())
        elif self.path == '/health':
            self.send_json_response({"status": "healthy", "message": "ClipsCommerce Core Pipeline Server"})
        elif self.path.startswith('/api/v1/pipeline/pipeline-status/'):
            job_id = self.path.split('/')[-1]
            self.send_json_response({
                "job_id": job_id,
                "status": "completed",
                "completion_percentage": 100,
                "message": "Pipeline completed successfully"
            })
        else:
            self.send_error(404, "Not Found")
    
    def do_POST(self):
        """Handle POST requests"""
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data.decode('utf-8')) if post_data else {}
        except:
            data = {}
        
        # CORS headers
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
        # Route handling
        if self.path == '/api/v1/pipeline/analyze-brand':
            response = self.handle_analyze_brand(data)
        elif self.path == '/api/v1/pipeline/generate-content-ideas':
            response = self.handle_generate_content_ideas(data)
        elif self.path == '/api/v1/pipeline/create-video-outlines':
            response = self.handle_create_video_outlines(data)
        elif self.path == '/api/v1/pipeline/generate-videos':
            response = self.handle_generate_videos(data)
        elif self.path == '/api/v1/pipeline/optimize-seo':
            response = self.handle_optimize_seo(data)
        elif self.path == '/api/v1/pipeline/full-pipeline':
            response = self.handle_full_pipeline(data)
        else:
            response = {"error": "Endpoint not found"}
        
        self.wfile.write(json.dumps(response, indent=2).encode())
    
    def do_OPTIONS(self):
        """Handle preflight requests"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def send_json_response(self, data):
        """Send JSON response with CORS headers"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode())
    
    def handle_analyze_brand(self, data):
        """Mock brand analysis"""
        brand_url = data.get('brand_url', '')
        
        # Mock brand data
        brand_data = {
            "name": "Example Brand",
            "description": "A modern e-commerce brand focused on innovative products",
            "logo_url": "https://example.com/logo.png",
            "target_audience": {
                "demographics": [{"segment": "young_adults", "score": 3}],
                "interests": [{"segment": "tech", "score": 2}]
            },
            "value_proposition": "Innovative products that make life easier",
            "brand_voice": {"primary_voice": "casual", "scores": {"casual": 3, "friendly": 2}},
            "social_links": {"instagram": "https://instagram.com/examplebrand"},
            "contact_info": {"email": "hello@example.com"}
        }
        
        # Mock products data
        products = [
            {
                "name": "Smart Water Bottle",
                "price": "$49.99",
                "description": "Temperature-controlled smart water bottle with app connectivity",
                "images": ["https://example.com/product1.jpg"],
                "features": ["Temperature control", "App connectivity", "Leak-proof design"],
                "benefits": ["stays hydrated", "tracks water intake"],
                "use_cases": ["perfect for workouts", "ideal for office use"],
                "url": f"{brand_url}/products/smart-water-bottle"
            },
            {
                "name": "Wireless Charging Pad",
                "price": "$29.99", 
                "description": "Fast wireless charging pad compatible with all devices",
                "images": ["https://example.com/product2.jpg"],
                "features": ["Fast charging", "Universal compatibility", "LED indicators"],
                "benefits": ["reduces cable clutter", "convenient charging"],
                "use_cases": ["great for desk setup", "perfect for nightstand"],
                "url": f"{brand_url}/products/wireless-charging-pad"
            }
        ]
        
        return {
            "success": True,
            "brand": brand_data,
            "products": products,
            "total_products": len(products),
            "message": "Brand analysis completed successfully"
        }
    
    def handle_generate_content_ideas(self, data):
        """Mock content idea generation"""
        brand_data = data.get('brand_data', {})
        products = data.get('products', [])
        content_count = data.get('content_count', 5)
        
        content_ideas = []
        
        for i in range(min(content_count, 10)):
            idea = {
                "title": f"Viral Content Idea #{i+1}",
                "hooks": [
                    {
                        "text": f"You won't believe what this {products[0]['name'] if products else 'product'} can do! 🤯",
                        "pattern": "curiosity_gap",
                        "viral_score": 8.5 + (i * 0.1),
                        "emotion": "amazement",
                        "platform": "tiktok",
                        "reasoning": "Strong curiosity gap with emotional trigger",
                        "improvements": ["Add specific numbers", "Include urgency"]
                    }
                ],
                "content_pillar": f"Product Demo #{i+1}",
                "target_audience": "tech-savvy millennials",
                "estimated_engagement": 0.75 + (i * 0.05),
                "content_type": "video",
                "keywords": ["viral", "trending", brand_data.get('name', 'brand').lower()],
                "trending_topics": ["productivity hacks", "tech reviews"],
                "created_at": time.time()
            }
            content_ideas.append(idea)
        
        return {
            "success": True,
            "content_ideas": content_ideas,
            "total_ideas": len(content_ideas),
            "message": "Content ideas generated successfully"
        }
    
    def handle_create_video_outlines(self, data):
        """Mock video outline creation"""
        content_ideas = data.get('content_ideas', [])
        brand_data = data.get('brand_data', {})
        
        video_outlines = []
        
        for idea in content_ideas[:5]:  # Limit to 5 outlines
            outline = {
                "content_idea": idea,
                "hook": idea.get('hooks', [{}])[0],
                "total_duration": 30,
                "scenes": [
                    {
                        "scene_number": 1,
                        "timing": "0-3s",
                        "type": "hook",
                        "visual": "Close-up product shot with dynamic movement",
                        "dialogue": idea.get('hooks', [{}])[0].get('text', 'Amazing content!'),
                        "text_overlay": "WAIT FOR IT...",
                        "transition": "Quick cut"
                    },
                    {
                        "scene_number": 2,
                        "timing": "3-8s",
                        "type": "problem",
                        "visual": "Problem situation or before state",
                        "dialogue": "You know that frustrating moment when...",
                        "text_overlay": "THE PROBLEM",
                        "transition": "Smooth transition"
                    },
                    {
                        "scene_number": 3,
                        "timing": "8-25s",
                        "type": "solution",
                        "visual": "Product demonstration solving the problem",
                        "dialogue": "Well, here's the game-changing solution!",
                        "text_overlay": "MIND BLOWN 🤯",
                        "transition": "Quick reveal"
                    },
                    {
                        "scene_number": 4,
                        "timing": "25-30s",
                        "type": "cta",
                        "visual": "Brand logo with clear call-to-action",
                        "dialogue": f"Get yours from {brand_data.get('name', 'our brand')} now!",
                        "text_overlay": "LINK IN BIO",
                        "transition": "Fade out"
                    }
                ],
                "metadata": {
                    "target_platform": "tiktok",
                    "video_style": "fast-paced",
                    "music_style": "upbeat trending",
                    "hashtags": ["#viral", "#trending", f"#{brand_data.get('name', 'brand').lower()}"]
                }
            }
            video_outlines.append(outline)
        
        return {
            "success": True,
            "video_outlines": video_outlines,
            "total_outlines": len(video_outlines),
            "message": "Video outlines created successfully"
        }
    
    def handle_generate_videos(self, data):
        """Mock video generation"""
        video_outlines = data.get('video_outlines', [])
        
        return {
            "success": True,
            "message": "Video generation started in background",
            "total_videos": len(video_outlines),
            "status": "processing",
            "estimated_completion": time.time() + 300  # 5 minutes from now
        }
    
    def handle_optimize_seo(self, data):
        """Mock SEO optimization"""
        video_outlines = data.get('video_outlines', [])
        brand_data = data.get('brand_data', {})
        
        optimized_content = []
        
        for outline in video_outlines:
            seo_data = {
                "title_options": [
                    "This Product Will Change Your Life Forever! 🤯",
                    "Why Everyone is Obsessed with This Gadget",
                    "The Secret Product Influencers Don't Want You to Know",
                    "I Tried This for 30 Days - Results Will Shock You",
                    "This is Going Viral for All the Right Reasons"
                ],
                "description": f"🔥 Amazing content from {brand_data.get('name', 'our brand')}! You won't believe what this product can do. Check out this viral video and see why everyone is talking about it. Link in bio for exclusive deals! #viral #trending #musthave",
                "hashtags": [
                    "#viral", "#trending", "#fyp", "#amazing", "#musthave",
                    "#productreview", "#lifehack", "#gamechanging", "#innovation",
                    f"#{brand_data.get('name', 'brand').lower()}"
                ],
                "keywords": ["viral content", "trending product", "game changer", "must have", "life hack"],
                "call_to_action": {
                    "primary": "Check the link in bio to get yours now!",
                    "secondary": "Save this for later - you'll thank me!",
                    "social": f"Follow @{brand_data.get('name', 'brand').lower()} for more amazing content!"
                },
                "thumbnails": [
                    {
                        "visual": "Product with dramatic lighting and surprised face",
                        "text": "VIRAL!",
                        "colors": "Bold red and white contrast",
                        "emotion": "Excitement and surprise",
                        "appeal": "High contrast draws immediate attention"
                    }
                ],
                "posting_strategy": {
                    "best_days": ["Tuesday", "Thursday", "Friday"],
                    "best_times": ["6-10am", "7-9pm"],
                    "peak_engagement": "Thursday 7pm",
                    "posting_frequency": "3-5 times per week",
                    "engagement_window": "First 2 hours are critical"
                }
            }
            
            optimized_content.append({
                "video_outline": outline,
                "seo_optimization": seo_data
            })
        
        return {
            "success": True,
            "optimized_content": optimized_content,
            "total_optimized": len(optimized_content),
            "message": "SEO optimization completed successfully"
        }
    
    def handle_full_pipeline(self, data):
        """Mock full pipeline execution"""
        brand_url = data.get('brand_url', '')
        content_count = data.get('content_count', 5)
        
        # Simulate running the full pipeline
        brand_response = self.handle_analyze_brand({"brand_url": brand_url})
        
        content_response = self.handle_generate_content_ideas({
            "brand_data": brand_response["brand"],
            "products": brand_response["products"],
            "content_count": content_count
        })
        
        outline_response = self.handle_create_video_outlines({
            "content_ideas": content_response["content_ideas"],
            "brand_data": brand_response["brand"]
        })
        
        seo_response = self.handle_optimize_seo({
            "video_outlines": outline_response["video_outlines"],
            "brand_data": brand_response["brand"]
        })
        
        return {
            "success": True,
            "pipeline_results": {
                "brand_analysis": {
                    "brand": brand_response["brand"],
                    "products_count": len(brand_response["products"])
                },
                "content_ideas": content_response["content_ideas"],
                "video_outlines": outline_response["video_outlines"],
                "seo_optimized_content": seo_response["optimized_content"]
            },
            "video_generation_status": "started",
            "message": "Full pipeline completed successfully - all steps executed!"
        }

def start_server(port=8000):
    """Start the simple test server"""
    server_address = ('', port)
    httpd = HTTPServer(server_address, CorePipelineHandler)
    
    print(f"""
🚀 ClipsCommerce Core Pipeline Test Server Started!

🌐 Server running at: http://localhost:{port}
📋 Test Interface: http://localhost:{port}
❤️  Health Check: http://localhost:{port}/health

📡 API Endpoints:
   POST /api/v1/pipeline/analyze-brand
   POST /api/v1/pipeline/generate-content-ideas  
   POST /api/v1/pipeline/create-video-outlines
   POST /api/v1/pipeline/generate-videos
   POST /api/v1/pipeline/optimize-seo
   POST /api/v1/pipeline/full-pipeline

Press Ctrl+C to stop the server
    """)
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Server stopped!")
        httpd.server_close()

if __name__ == "__main__":
    start_server()