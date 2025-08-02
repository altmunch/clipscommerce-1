"use client";

import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/Tabs";
import { Button } from "@/components/ui/Button";
import { Brain, Rocket, TrendingUp, Palette, ChevronDown } from "lucide-react";
import StrategyTab from "./tabs/StrategyTab";
import PipelineTab from "./tabs/PipelineTab";
import ResultsTab from "./tabs/ResultsTab";
import BrandKitTab from "./tabs/BrandKitTab";

export default function Dashboard() {
  return (
    <div className="min-h-screen bg-primary-bg">
      {/* Top Navigation */}
      <div className="border-b border-primary-border bg-primary-bg">
        <div className="max-w-7xl mx-auto px-6">
          <Tabs defaultValue="strategy">
            <div className="flex items-center justify-between py-4">
              {/* Brand Logo */}
              <div className="flex items-center space-x-8">
                <h1 className="text-2xl font-bold text-primary-text">ViralOS</h1>
                <TabsList>
                  <TabsTrigger value="strategy" className="flex items-center space-x-2">
                    <Brain className="w-4 h-4" />
                    <span>Strategy</span>
                  </TabsTrigger>
                  <TabsTrigger value="pipeline" className="flex items-center space-x-2">
                    <Rocket className="w-4 h-4" />
                    <span>Pipeline</span>
                  </TabsTrigger>
                  <TabsTrigger value="results" className="flex items-center space-x-2">
                    <TrendingUp className="w-4 h-4" />
                    <span>Results</span>
                  </TabsTrigger>
                  <TabsTrigger value="brand-kit" className="flex items-center space-x-2">
                    <Palette className="w-4 h-4" />
                    <span>Brand Kit</span>
                  </TabsTrigger>
                </TabsList>
              </div>

              {/* Header Controls */}
              <div className="flex items-center space-x-4">
                <div className="flex items-center space-x-2 text-primary-text-secondary">
                  <span className="text-sm">Displaying for:</span>
                  <button className="flex items-center space-x-1 text-primary-text hover:text-primary-accent">
                    <span className="font-medium">YourBrand.com</span>
                    <ChevronDown className="w-4 h-4" />
                  </button>
                </div>
                <Button>
                  + New Campaign
                </Button>
              </div>
            </div>

            {/* Tab Content */}
            <div className="pb-8">
              <TabsContent value="strategy">
                <StrategyTab />
              </TabsContent>
              <TabsContent value="pipeline">
                <PipelineTab />
              </TabsContent>
              <TabsContent value="results">
                <ResultsTab />
              </TabsContent>
              <TabsContent value="brand-kit">
                <BrandKitTab />
              </TabsContent>
            </div>
          </Tabs>
        </div>
      </div>
    </div>
  );
}