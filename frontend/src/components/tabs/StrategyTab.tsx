"use client";

import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Plus, Calendar, Target } from "lucide-react";
import { useBrands, useCampaigns, useBrandKit } from "@/hooks/useApi";
import { useState } from "react";
import { format } from "date-fns";

export default function StrategyTab() {
  const [selectedBrandId, setSelectedBrandId] = useState<string>("");
  const { data: brands } = useBrands();
  const { data: campaignsData } = useCampaigns(selectedBrandId);
  const { data: brandKit } = useBrandKit(selectedBrandId);

  // Use first brand as default if available
  const currentBrandId = selectedBrandId || brands?.data?.[0]?.brandId || "";
  
  const campaigns = campaignsData?.data || [];
  const contentPillars = brandKit?.pillars || [
    "Product Education",
    "User Testimonials",
    "Behind the Scenes",
    "Industry Tips",
    "Product Demos",
  ];

  return (
    <div className="max-w-7xl mx-auto px-6">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Left Column - Campaigns */}
        <div>
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-semibold text-primary-text">Campaigns</h2>
            <Button size="sm" className="flex items-center space-x-2">
              <Plus className="w-4 h-4" />
              <span>New Campaign</span>
            </Button>
          </div>

          <div className="space-y-4">
            {campaigns.length === 0 ? (
              <Card>
                <CardContent className="p-6 text-center">
                  <p className="text-primary-text-secondary mb-4">No campaigns yet</p>
                  <Button size="sm">Create Your First Campaign</Button>
                </CardContent>
              </Card>
            ) : (
              campaigns.map((campaign: any) => (
                <Card key={campaign.campaignId}>
                  <CardContent className="p-6">
                    <div className="flex items-start justify-between mb-4">
                      <div>
                        <h3 className="font-semibold text-primary-text mb-1">
                          {campaign.name}
                        </h3>
                        <div className="flex items-center text-sm text-primary-text-secondary space-x-4">
                          <div className="flex items-center space-x-1">
                            <Calendar className="w-4 h-4" />
                            <span>
                              {campaign.startDate && campaign.endDate
                                ? `${format(new Date(campaign.startDate), 'MMM d')} - ${format(new Date(campaign.endDate), 'MMM d, yyyy')}`
                                : 'No dates set'
                              }
                            </span>
                          </div>
                          <div className="flex items-center space-x-1">
                            <Target className="w-4 h-4" />
                            <span>{campaign.goal || 'No goal set'}</span>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Progress Bar - For demo purposes, showing random progress */}
                    <div className="mb-2">
                      <div className="flex justify-between text-sm mb-1">
                        <span className="text-primary-text-secondary">Progress</span>
                        <span className="text-primary-text">65%</span>
                      </div>
                      <div className="w-full bg-primary-border rounded-full h-2">
                        <div
                          className="bg-primary-accent h-2 rounded-full transition-all"
                          style={{ width: '65%' }}
                        />
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))
            )}
          </div>
        </div>

        {/* Right Column - Content Pillars */}
        <div>
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-semibold text-primary-text">Content Pillars</h2>
            <Button size="sm" variant="secondary" className="flex items-center space-x-2">
              <Plus className="w-4 h-4" />
              <span>Add Pillar</span>
            </Button>
          </div>

          <Card>
            <CardContent className="p-6">
              <div className="space-y-3">
                {contentPillars.map((pillar, index) => (
                  <div
                    key={index}
                    className="flex items-center justify-between p-3 bg-primary-bg rounded-default border border-primary-border"
                  >
                    <span className="text-primary-text">{pillar}</span>
                    <button className="text-primary-text-secondary hover:text-red-400 text-sm">
                      Remove
                    </button>
                  </div>
                ))}
                
                <div className="mt-4 pt-4 border-t border-primary-border">
                  <div className="flex items-center space-x-2">
                    <input
                      type="text"
                      placeholder="Add new content pillar..."
                      className="flex-1 px-3 py-2 bg-primary-bg border border-primary-border rounded-default text-primary-text placeholder-primary-text-secondary focus:outline-none focus:ring-2 focus:ring-primary-accent"
                    />
                    <Button size="sm">Add</Button>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}