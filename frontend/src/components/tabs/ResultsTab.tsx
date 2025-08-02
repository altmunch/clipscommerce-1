"use client";

import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { TrendingUp, TrendingDown, ChevronDown, ArrowUpDown } from "lucide-react";
import { useBrands, useKpis, useChartData, useContentPerformance } from "@/hooks/useApi";
import { useState } from "react";

export default function ResultsTab() {
  const [selectedMetric, setSelectedMetric] = useState("revenue");
  const { data: brands } = useBrands();
  const currentBrandId = brands?.data?.[0]?.brandId || "";
  
  const { data: kpisData } = useKpis(currentBrandId);
  const { data: chartData } = useChartData(currentBrandId, selectedMetric);
  const { data: contentData } = useContentPerformance(currentBrandId);

  const kpis = kpisData ? [
    {
      title: "Attributed Revenue",
      value: `$${kpisData.attributedRevenue?.toLocaleString() || '0'}`,
      change: "+12%",
      isPositive: true
    },
    {
      title: "Total Views",
      value: `${(kpisData.totalViews / 1000000).toFixed(1)}M`,
      change: "+8%",
      isPositive: true
    },
    {
      title: "Clicks Driven",
      value: kpisData.clicksDriven?.toLocaleString() || '0',
      change: "-3%",
      isPositive: false
    },
    {
      title: "Avg Conv Rate",
      value: `${(kpisData.avgConversionRate * 100).toFixed(1)}%`,
      change: "+5%",
      isPositive: true
    }
  ] : [];

  const contentData = [
    {
      id: 1,
      thumbnail: "/api/placeholder/60/60",
      title: "3 Mistakes You're Making...",
      views: "105,000",
      clicks: 452,
      revenue: "$2,150"
    },
    {
      id: 2,
      thumbnail: "/api/placeholder/60/60",
      title: "This ONE Trick Will...",
      views: "87,500",
      clicks: 341,
      revenue: "$1,890"
    },
    {
      id: 3,
      thumbnail: "/api/placeholder/60/60",
      title: "Why Everyone is Switching...",
      views: "62,300",
      clicks: 289,
      revenue: "$1,420"
    },
    {
      id: 4,
      thumbnail: "/api/placeholder/60/60",
      title: "The Secret Nobody Tells...",
      views: "45,200",
      clicks: 198,
      revenue: "$980"
    }
  ];

  // Mock chart data points
  const chartData = [
    { date: "Dec 1", value: 850 },
    { date: "Dec 2", value: 920 },
    { date: "Dec 3", value: 880 },
    { date: "Dec 4", value: 1100 },
    { date: "Dec 5", value: 1250 },
    { date: "Dec 6", value: 1180 },
    { date: "Dec 7", value: 1350 }
  ];

  const maxValue = Math.max(...chartData.map(d => d.value));

  return (
    <div className="max-w-7xl mx-auto px-6 space-y-8">
      {/* KPI Bar */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {kpis.map((kpi, index) => (
          <Card key={index}>
            <CardContent className="p-6">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-primary-text-secondary">
                  {kpi.title}
                </span>
                <div className={`flex items-center space-x-1 text-sm ${
                  kpi.isPositive ? 'text-green-400' : 'text-red-400'
                }`}>
                  {kpi.isPositive ? (
                    <TrendingUp className="w-3 h-3" />
                  ) : (
                    <TrendingDown className="w-3 h-3" />
                  )}
                  <span>{kpi.change}</span>
                </div>
              </div>
              <div className="text-2xl font-bold text-primary-text">
                {kpi.value}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Performance Chart */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Performance Over Time</CardTitle>
            <div className="flex items-center space-x-2">
              <Button variant="ghost" size="sm" className="flex items-center space-x-1">
                <span>Revenue</span>
                <ChevronDown className="w-4 h-4" />
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="h-64 flex items-end space-x-2">
            {chartData.map((point, index) => (
              <div key={index} className="flex-1 flex flex-col items-center">
                <div 
                  className="w-full bg-primary-accent rounded-t-sm transition-all hover:bg-purple-600"
                  style={{ 
                    height: `${(point.value / maxValue) * 200}px`,
                    minHeight: '4px'
                  }}
                />
                <span className="text-xs text-primary-text-secondary mt-2">
                  {point.date}
                </span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Content Performance Table */}
      <Card>
        <CardHeader>
          <CardTitle>Content Performance</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-primary-border">
                  <th className="text-left py-3 px-4 font-medium text-primary-text-secondary">
                    <Button variant="ghost" size="sm" className="flex items-center space-x-1 p-0 h-auto">
                      <span>Content</span>
                      <ArrowUpDown className="w-3 h-3" />
                    </Button>
                  </th>
                  <th className="text-left py-3 px-4 font-medium text-primary-text-secondary">
                    <Button variant="ghost" size="sm" className="flex items-center space-x-1 p-0 h-auto">
                      <span>Views</span>
                      <ArrowUpDown className="w-3 h-3" />
                    </Button>
                  </th>
                  <th className="text-left py-3 px-4 font-medium text-primary-text-secondary">
                    <Button variant="ghost" size="sm" className="flex items-center space-x-1 p-0 h-auto">
                      <span>Clicks</span>
                      <ArrowUpDown className="w-3 h-3" />
                    </Button>
                  </th>
                  <th className="text-right py-3 px-4 font-medium text-primary-text-secondary">
                    <Button variant="ghost" size="sm" className="flex items-center space-x-1 p-0 h-auto ml-auto">
                      <span>Revenue</span>
                      <ArrowUpDown className="w-3 h-3" />
                    </Button>
                  </th>
                </tr>
              </thead>
              <tbody>
                {contentData.map((item) => (
                  <tr key={item.id} className="border-b border-primary-border hover:bg-primary-card/50">
                    <td className="py-4 px-4">
                      <div className="flex items-center space-x-3">
                        <div className="w-12 h-12 bg-primary-bg rounded-default border border-primary-border flex items-center justify-center">
                          <span className="text-xs text-primary-text-secondary">IMG</span>
                        </div>
                        <span className="text-primary-text font-medium">{item.title}</span>
                      </div>
                    </td>
                    <td className="py-4 px-4 text-primary-text">{item.views}</td>
                    <td className="py-4 px-4 text-primary-text">{item.clicks}</td>
                    <td className="py-4 px-4 text-right text-primary-text font-semibold">{item.revenue}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}