"use client";

import { Card, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { 
  Lightbulb, 
  FileText, 
  Film, 
  Zap, 
  Calendar,
  CheckCircle,
  XCircle,
  Play,
  Upload,
  Instagram,
  // TikTok icon not in Lucide, using Music instead
  Music
} from "lucide-react";

export default function PipelineTab() {
  const columns = [
    {
      id: "viral-generator",
      title: "Viral Generator",
      icon: Lightbulb,
      items: [
        {
          id: 1,
          hook: "3 Mistakes You're Making With Your Product",
          viralScore: 9.1,
          status: "pending"
        },
        {
          id: 2,
          hook: "This ONE Trick Will Change Everything",
          viralScore: 8.7,
          status: "pending"
        }
      ]
    },
    {
      id: "blueprint-architect",
      title: "Blueprint Architect",
      icon: FileText,
      items: [
        {
          id: 3,
          hook: "Why Everyone is Switching to This",
          status: "script_ready",
          hasScript: true,
          hasShotList: true
        }
      ]
    },
    {
      id: "turbo-editor",
      title: "Turbo Editor",
      icon: Film,
      items: [
        {
          id: 4,
          hook: "The Secret Nobody Tells You",
          status: "editing",
          videoPreview: "/api/placeholder/200/150"
        }
      ]
    },
    {
      id: "conversion-catalyst",
      title: "Conversion Catalyst",
      icon: Zap,
      items: [
        {
          id: 5,
          hook: "This Will Blow Your Mind",
          status: "optimized",
          caption: "Ready",
          hashtags: "Ready",
          cta: "Ready"
        }
      ]
    },
    {
      id: "publishing-queue",
      title: "Publishing Queue",
      icon: Calendar,
      items: [
        {
          id: 6,
          hook: "Game-Changing Productivity Hack",
          status: "scheduled",
          scheduledDate: "Dec 15, 2025 6:00 PM",
          platforms: ["instagram", "tiktok"]
        }
      ]
    }
  ];

  const renderCard = (item: any, columnId: string) => {
    return (
      <Card key={item.id} className="mb-4 cursor-pointer hover:ring-2 hover:ring-primary-accent transition-all">
        <CardContent className="p-4">
          <div className="mb-3">
            <h4 className="font-medium text-primary-text text-sm leading-tight">
              {item.hook}
            </h4>
          </div>

          {columnId === "viral-generator" && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs text-primary-text-secondary">Viral Score</span>
                <span className="text-sm font-semibold text-primary-accent">
                  {item.viralScore}
                </span>
              </div>
              <div className="flex space-x-2">
                <Button size="sm" className="flex-1">
                  <CheckCircle className="w-3 h-3 mr-1" />
                  Approve
                </Button>
                <Button size="sm" variant="secondary" className="flex-1">
                  <XCircle className="w-3 h-3 mr-1" />
                  Reject
                </Button>
              </div>
            </div>
          )}

          {columnId === "blueprint-architect" && (
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div className={`flex items-center space-x-1 ${item.hasScript ? 'text-green-400' : 'text-primary-text-secondary'}`}>
                    <FileText className="w-3 h-3" />
                    <span className="text-xs">Script</span>
                  </div>
                  <div className={`flex items-center space-x-1 ${item.hasShotList ? 'text-green-400' : 'text-primary-text-secondary'}`}>
                    <Film className="w-3 h-3" />
                    <span className="text-xs">Shot List</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {columnId === "turbo-editor" && (
            <div className="space-y-3">
              <div className="bg-primary-bg rounded-default h-20 flex items-center justify-center border border-primary-border">
                {item.videoPreview ? (
                  <div className="text-center">
                    <Play className="w-6 h-6 text-primary-accent mx-auto mb-1" />
                    <span className="text-xs text-primary-text-secondary">Video Preview</span>
                  </div>
                ) : (
                  <div className="text-center">
                    <Upload className="w-6 h-6 text-primary-text-secondary mx-auto mb-1" />
                    <span className="text-xs text-primary-text-secondary">Upload Area</span>
                  </div>
                )}
              </div>
            </div>
          )}

          {columnId === "conversion-catalyst" && (
            <div className="space-y-2">
              <div className="grid grid-cols-3 gap-2 text-xs">
                <div className="text-center">
                  <div className={`w-2 h-2 rounded-full mx-auto mb-1 ${item.caption === 'Ready' ? 'bg-green-400' : 'bg-primary-text-secondary'}`} />
                  <span className="text-primary-text-secondary">Caption</span>
                </div>
                <div className="text-center">
                  <div className={`w-2 h-2 rounded-full mx-auto mb-1 ${item.hashtags === 'Ready' ? 'bg-green-400' : 'bg-primary-text-secondary'}`} />
                  <span className="text-primary-text-secondary">Hashtags</span>
                </div>
                <div className="text-center">
                  <div className={`w-2 h-2 rounded-full mx-auto mb-1 ${item.cta === 'Ready' ? 'bg-green-400' : 'bg-primary-text-secondary'}`} />
                  <span className="text-primary-text-secondary">CTA</span>
                </div>
              </div>
            </div>
          )}

          {columnId === "publishing-queue" && (
            <div className="space-y-3">
              <div>
                <p className="text-xs text-primary-text-secondary mb-1">Scheduled for</p>
                <p className="text-sm text-primary-text">{item.scheduledDate}</p>
              </div>
              <div className="flex items-center space-x-2">
                {item.platforms.includes("instagram") && (
                  <Instagram className="w-4 h-4 text-pink-500" />
                )}
                {item.platforms.includes("tiktok") && (
                  <Music className="w-4 h-4 text-primary-text" />
                )}
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    );
  };

  return (
    <div className="max-w-7xl mx-auto px-6">
      <div className="flex space-x-6 overflow-x-auto pb-6">
        {columns.map((column) => {
          const Icon = column.icon;
          return (
            <div key={column.id} className="min-w-80 flex-shrink-0">
              <div className="flex items-center space-x-2 mb-4">
                <Icon className="w-5 h-5 text-primary-accent" />
                <h3 className="font-semibold text-primary-text">{column.title}</h3>
                <span className="text-xs text-primary-text-secondary bg-primary-card px-2 py-1 rounded-full">
                  {column.items.length}
                </span>
              </div>
              
              <div className="space-y-4">
                {column.items.map((item) => renderCard(item, column.id))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}