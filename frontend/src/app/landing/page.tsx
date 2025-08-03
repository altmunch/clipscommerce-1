"use client";

import { useState } from 'react';
import { Button } from '@/components/ui/Button';
import { Card, CardContent } from '@/components/ui/Card';
import { Brain, Rocket, TrendingUp, Shield, CheckCircle, ChevronRight, Play, BarChart3 } from 'lucide-react';
import Link from 'next/link';

export default function LandingPage() {
  const [selectedPlan, setSelectedPlan] = useState<string>('autonomous');

  const handleDemoRequest = (plan: string = 'autonomous') => {
    setSelectedPlan(plan);
    // Redirect to signup with plan parameter
    window.location.href = `/auth/signup?plan=${plan}`;
  };

  return (
    <div className="min-h-screen bg-primary-bg">
      {/* Hero Section */}
      <section className="relative min-h-screen flex items-center overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-primary-accent/5 to-transparent" />
        <div className="max-w-7xl mx-auto px-6 relative z-10">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
            <div className="space-y-8">
              <div className="space-y-6">
                <h1 className="text-5xl lg:text-7xl font-bold text-primary-text leading-tight">
                  Stop Guessing.
                  <span className="block text-transparent bg-gradient-to-r from-primary-accent to-chart-pink bg-clip-text">
                    Start Scaling.
                  </span>
                </h1>
                <p className="text-xl text-primary-text-secondary max-w-xl leading-relaxed">
                  The Autonomous Ad System for DTC brands. We deliver campaign-ready, 
                  AI-powered video creative—human-reviewed and optimized for ROAS—to your inbox, every week.
                </p>
              </div>
              
              <div className="flex flex-col sm:flex-row gap-4">
                <Button 
                  size="lg" 
                  className="text-lg px-8 py-4 bg-gradient-to-r from-primary-accent to-chart-pink hover:opacity-90 transition-all transform hover:scale-105"
                  onClick={() => handleDemoRequest()}
                >
                  Request Your Growth Demo
                  <ChevronRight className="w-5 h-5 ml-2" />
                </Button>
                <Button 
                  variant="secondary" 
                  size="lg" 
                  className="text-lg px-8 py-4 border-primary-accent text-primary-accent hover:bg-primary-accent/10"
                >
                  <Play className="w-5 h-5 mr-2" />
                  Watch Demo
                </Button>
              </div>
            </div>

            {/* Hero Visual */}
            <div className="relative">
              <div className="relative bg-primary-card rounded-2xl p-8 border border-primary-border">
                <div className="space-y-6">
                  <div className="flex items-center justify-between">
                    <h3 className="text-lg font-semibold text-primary-text">ViralOS Dashboard</h3>
                    <div className="flex space-x-2">
                      <div className="w-3 h-3 bg-red-500 rounded-full"></div>
                      <div className="w-3 h-3 bg-yellow-500 rounded-full"></div>
                      <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                    </div>
                  </div>
                  
                  <div className="space-y-4">
                    <div className="grid grid-cols-3 gap-4">
                      <div className="bg-primary-bg rounded-lg p-4 border border-primary-border">
                        <div className="text-2xl font-bold text-chart-teal">$47k</div>
                        <div className="text-sm text-primary-text-secondary">Revenue</div>
                      </div>
                      <div className="bg-primary-bg rounded-lg p-4 border border-primary-border">
                        <div className="text-2xl font-bold text-chart-pink">2.4M</div>
                        <div className="text-sm text-primary-text-secondary">Views</div>
                      </div>
                      <div className="bg-primary-bg rounded-lg p-4 border border-primary-border">
                        <div className="text-2xl font-bold text-chart-yellow">4.2%</div>
                        <div className="text-sm text-primary-text-secondary">CTR</div>
                      </div>
                    </div>
                    
                    <div className="bg-primary-bg rounded-lg p-4 border border-primary-border">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-primary-text font-medium">Campaign Performance</span>
                        <BarChart3 className="w-4 h-4 text-primary-accent" />
                      </div>
                      <div className="space-y-2">
                        <div className="flex justify-between text-sm">
                          <span className="text-primary-text-secondary">Holiday Sale 2025</span>
                          <span className="text-chart-teal">+127%</span>
                        </div>
                        <div className="w-full bg-primary-border rounded-full h-2">
                          <div className="bg-gradient-to-r from-primary-accent to-chart-teal h-2 rounded-full" style={{width: '78%'}}></div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Social Proof */}
      <section className="py-16 border-t border-primary-border bg-primary-card/30">
        <div className="max-w-7xl mx-auto px-6 text-center">
          <h2 className="text-2xl font-semibold text-primary-text mb-8">
            The Unfair Advantage for the Next Generation of DTC Leaders
          </h2>
          <div className="flex justify-center items-center space-x-12 opacity-60">
            {['Brand A', 'Brand B', 'Brand C', 'Brand D', 'Brand E'].map((brand, index) => (
              <div key={index} className="bg-primary-card px-6 py-3 rounded-lg border border-primary-border">
                <span className="text-primary-text font-medium">{brand}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Problem Section */}
      <section className="py-20">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold text-primary-text mb-6">
              Your Growth Has a Bottleneck. It's Creative.
            </h2>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {[
              {
                title: "Scaling ad spend, but ROAS is dropping?",
                description: "Your winning creatives are burning out faster than you can replace them."
              },
              {
                title: "Constantly battling creative fatigue?", 
                description: "Your audience has seen everything, and performance is declining week over week."
              },
              {
                title: "Tired of managing unreliable freelancers and slow agencies?",
                description: "Endless revisions, missed deadlines, and creative that doesn't convert."
              },
              {
                title: "Wasting hours trying to be a creative director instead of a founder?",
                description: "You should be scaling your business, not micromanaging video edits."
              }
            ].map((problem, index) => (
              <Card key={index} className="group hover:border-primary-accent transition-all">
                <CardContent className="p-8">
                  <div className="flex items-start space-x-4">
                    <CheckCircle className="w-6 h-6 text-primary-accent flex-shrink-0 mt-1" />
                    <div>
                      <h3 className="text-lg font-semibold text-primary-text mb-2">{problem.title}</h3>
                      <p className="text-primary-text-secondary">{problem.description}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Solution Section */}
      <section className="py-20 bg-primary-card/20">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold text-primary-text mb-6">
              This Isn't Another Tool. It's a System You Install.
            </h2>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-12">
            {[
              {
                icon: <Brain className="w-8 h-8" />,
                step: "1",
                title: "Connect Your Stack",
                description: "We integrate with your store and ad platforms with \"white-glove\" onboarding. No technical setup required."
              },
              {
                icon: <Rocket className="w-8 h-8" />,
                step: "2", 
                title: "AI Analyzes & Creates",
                description: "Our system analyzes your data, competitors, and trends to generate optimized video campaigns tailored to your brand."
              },
              {
                icon: <TrendingUp className="w-8 h-8" />,
                step: "3",
                title: "Approve & Scale", 
                description: "You receive a weekly \"Creative Drop.\" Approve your favorites and launch. Scale what works, iterate what doesn't."
              }
            ].map((step, index) => (
              <div key={index} className="text-center group">
                <div className="relative mb-6">
                  <div className="w-16 h-16 bg-gradient-to-r from-primary-accent to-chart-pink rounded-full flex items-center justify-center mx-auto mb-4 group-hover:scale-110 transition-transform">
                    {step.icon}
                  </div>
                  <div className="absolute -top-2 -right-2 w-8 h-8 bg-primary-card border-2 border-primary-accent rounded-full flex items-center justify-center">
                    <span className="text-sm font-bold text-primary-accent">{step.step}</span>
                  </div>
                </div>
                <h3 className="text-xl font-semibold text-primary-text mb-4">{step.title}</h3>
                <p className="text-primary-text-secondary">{step.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Value Stack */}
      <section className="py-20">
        <div className="max-w-5xl mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold text-primary-text mb-6">
              Your Complete Creative Partner, Powered by AI
            </h2>
          </div>
          
          <Card className="bg-primary-card border-primary-border">
            <CardContent className="p-8">
              <div className="space-y-6">
                {[
                  { name: "Weekly AI-Generated & Human-Reviewed Creative Drop", value: "$5,000/mo" },
                  { name: "The Weekly \"ROAS Intelligence\" Report", value: "$2,000/mo" },
                  { name: "The \"Competitor Creative Scan\"", value: "$1,500/mo" },
                  { name: "A Dedicated \"AI Strategist\" via Slack", value: "$2,500/mo" },
                  { name: "\"White-Glove\" Onboarding & Integration", value: "$1,000" }
                ].map((item, index) => (
                  <div key={index} className="flex justify-between items-center py-4 border-b border-primary-border last:border-b-0">
                    <div className="flex items-center space-x-3">
                      <CheckCircle className="w-5 h-5 text-primary-accent" />
                      <span className="text-primary-text">{item.name}</span>
                    </div>
                    <span className="text-primary-accent font-semibold">{item.value}</span>
                  </div>
                ))}
                
                <div className="pt-6 border-t-2 border-primary-accent text-center">
                  <div className="text-primary-text-secondary mb-2">Total Value:</div>
                  <div className="text-4xl font-bold text-transparent bg-gradient-to-r from-primary-accent to-chart-pink bg-clip-text">
                    $12,000/month
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </section>

      {/* Pricing */}
      <section className="py-20 bg-primary-card/20">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold text-primary-text mb-6">Choose Your Growth Plan</h2>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-5xl mx-auto">
            {[
              { name: "Starter", price: "$249", period: "per month", description: "Perfect for testing the waters", plan: "starter" },
              { name: "Autonomous", price: "$749", period: "per month", description: "The complete system for serious growth", plan: "autonomous", featured: true },
              { name: "Enterprise", price: "Custom", period: "contact us", description: "For brands doing $10M+ annually", plan: "enterprise" }
            ].map((tier, index) => (
              <Card key={index} className={`relative ${tier.featured ? 'border-primary-accent bg-primary-accent/5 scale-105' : ''}`}>
                {tier.featured && (
                  <div className="absolute -top-4 left-1/2 transform -translate-x-1/2">
                    <div className="bg-gradient-to-r from-primary-accent to-chart-pink text-white px-4 py-1 rounded-full text-sm font-semibold">
                      Most Popular
                    </div>
                  </div>
                )}
                <CardContent className="p-8 text-center">
                  <h3 className="text-2xl font-semibold text-primary-text mb-2">{tier.name}</h3>
                  <div className="text-4xl font-bold text-primary-text mb-2">{tier.price}</div>
                  <div className="text-primary-text-secondary mb-6">{tier.period}</div>
                  <p className="text-primary-text-secondary mb-8">{tier.description}</p>
                  <Button 
                    className={`w-full ${tier.featured ? 'bg-gradient-to-r from-primary-accent to-chart-pink' : ''}`}
                    variant={tier.featured ? 'primary' : 'secondary'}
                    onClick={() => handleDemoRequest(tier.plan)}
                  >
                    {tier.plan === 'enterprise' ? 'Contact Sales' : 'Request Demo'}
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Guarantee */}
      <section className="py-20">
        <div className="max-w-4xl mx-auto px-6">
          <Card className="bg-primary-card border-primary-accent">
            <CardContent className="p-12 text-center">
              <div className="w-20 h-20 bg-gradient-to-r from-primary-accent to-chart-pink rounded-full flex items-center justify-center mx-auto mb-8">
                <Shield className="w-10 h-10" />
              </div>
              <h2 className="text-3xl font-bold text-primary-text mb-6">Our "Double Your CTR" Guarantee</h2>
              <p className="text-xl text-primary-text-secondary max-w-2xl mx-auto">
                We're so confident in our system that we guarantee to double your click-through rates 
                within 60 days, or we'll work for free until we do. You literally cannot lose.
              </p>
            </CardContent>
          </Card>
        </div>
      </section>

      {/* Final CTA */}
      <section className="py-20 bg-primary-card/30 text-center">
        <div className="max-w-4xl mx-auto px-6">
          <h2 className="text-4xl font-bold text-primary-text mb-6">Ready to Unbottleneck Your Growth?</h2>
          <p className="text-xl text-primary-text-secondary mb-12 max-w-2xl mx-auto">
            Join the next generation of DTC leaders who've solved the creative bottleneck.
          </p>
          <Button 
            size="lg" 
            className="text-xl px-12 py-6 bg-gradient-to-r from-primary-accent to-chart-pink hover:opacity-90 transition-all transform hover:scale-105"
            onClick={() => handleDemoRequest()}
          >
            Request Your Growth Demo
            <ChevronRight className="w-6 h-6 ml-2" />
          </Button>
        </div>
      </section>

      {/* Navigation Link for existing users */}
      <div className="fixed bottom-6 right-6">
        <Link href="/dashboard">
          <Button variant="secondary" size="sm" className="shadow-lg">
            Existing User? Dashboard →
          </Button>
        </Link>
      </div>
    </div>
  );
}