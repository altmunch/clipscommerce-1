"use client";

import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Upload, Plus, X } from "lucide-react";

export default function BrandKitTab() {
  const brandColors = [
    { name: "Primary", hex: "#A855F7", color: "bg-purple-500" },
    { name: "Secondary", hex: "#06B6D4", color: "bg-cyan-500" },
    { name: "Accent", hex: "#F59E0B", color: "bg-amber-500" },
  ];

  const assetLibrary = [
    { id: 1, name: "Logo_Main.png", type: "logo" },
    { id: 2, name: "Product_Hero.jpg", type: "product" },
    { id: 3, name: "BTS_Office.mp4", type: "video" },
    { id: 4, name: "Team_Photo.jpg", type: "team" },
    { id: 5, name: "Product_Demo.mp4", type: "video" },
    { id: 6, name: "Logo_White.png", type: "logo" },
  ];

  return (
    <div className="max-w-7xl mx-auto px-6">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
        {/* Left Column - Visual Identity */}
        <div className="space-y-6">
          <h2 className="text-xl font-semibold text-primary-text">Visual Identity</h2>
          
          {/* Logo Upload */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Brand Logo</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="border-2 border-dashed border-primary-border rounded-default p-8 text-center hover:border-primary-accent transition-colors cursor-pointer">
                <Upload className="w-8 h-8 text-primary-text-secondary mx-auto mb-3" />
                <p className="text-primary-text-secondary mb-2">
                  Drop your logo here or click to upload
                </p>
                <p className="text-sm text-primary-text-secondary">
                  PNG, JPG, SVG up to 5MB
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Color Palette */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg">Brand Colors</CardTitle>
                <Button size="sm" variant="secondary">
                  <Plus className="w-4 h-4 mr-1" />
                  Add Color
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {brandColors.map((color, index) => (
                  <div key={index} className="flex items-center space-x-4">
                    <div className={`w-12 h-12 rounded-default ${color.color} border border-primary-border`} />
                    <div className="flex-1">
                      <p className="text-primary-text font-medium">{color.name}</p>
                      <p className="text-primary-text-secondary text-sm">{color.hex}</p>
                    </div>
                    <input
                      type="text"
                      value={color.hex}
                      className="w-24 px-2 py-1 bg-primary-bg border border-primary-border rounded text-primary-text text-sm focus:outline-none focus:ring-2 focus:ring-primary-accent"
                      readOnly
                    />
                    <Button size="sm" variant="ghost">
                      <X className="w-4 h-4" />
                    </Button>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Right Column - Brand Voice */}
        <div className="space-y-6">
          <h2 className="text-xl font-semibold text-primary-text">Brand Voice</h2>
          
          {/* Brand Mission */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Brand Mission</CardTitle>
            </CardHeader>
            <CardContent>
              <textarea
                className="w-full h-24 p-3 bg-primary-bg border border-primary-border rounded-default text-primary-text placeholder-primary-text-secondary focus:outline-none focus:ring-2 focus:ring-primary-accent resize-none"
                placeholder="Describe your brand's mission and core values..."
                defaultValue="We empower entrepreneurs to build successful e-commerce businesses through innovative marketing automation and AI-powered insights."
              />
            </CardContent>
          </Card>

          {/* Language Do's */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Language Do's</CardTitle>
            </CardHeader>
            <CardContent>
              <textarea
                className="w-full h-32 p-3 bg-primary-bg border border-primary-border rounded-default text-primary-text placeholder-primary-text-secondary focus:outline-none focus:ring-2 focus:ring-primary-accent resize-none"
                placeholder="What language and tone should we use?"
                defaultValue="• Use conversational, friendly tone
• Focus on actionable insights
• Include data-driven statements
• Emphasize entrepreneurial mindset
• Use 'we' and 'our' to build community"
              />
            </CardContent>
          </Card>

          {/* Language Don'ts */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Language Don'ts</CardTitle>
            </CardHeader>
            <CardContent>
              <textarea
                className="w-full h-32 p-3 bg-primary-bg border border-primary-border rounded-default text-primary-text placeholder-primary-text-secondary focus:outline-none focus:ring-2 focus:ring-primary-accent resize-none"
                placeholder="What should we avoid in messaging?"
                defaultValue="• Avoid overly technical jargon
• Don't make unrealistic promises
• Avoid negative or fear-based messaging
• Don't use outdated slang or terms
• Avoid being too sales-heavy"
              />
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Asset Library - Full Width */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-xl">Asset Library</CardTitle>
            <Button className="flex items-center space-x-2">
              <Upload className="w-4 h-4" />
              <span>Upload Assets</span>
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
            {assetLibrary.map((asset) => (
              <div key={asset.id} className="group relative">
                <div className="aspect-square bg-primary-bg border border-primary-border rounded-default flex items-center justify-center hover:border-primary-accent transition-colors cursor-pointer">
                  <div className="text-center">
                    <div className="w-8 h-8 bg-primary-card rounded mx-auto mb-2 flex items-center justify-center">
                      <span className="text-xs font-medium text-primary-text-secondary">
                        {asset.type === "logo" ? "L" : asset.type === "video" ? "V" : "I"}
                      </span>
                    </div>
                    <p className="text-xs text-primary-text-secondary px-1 leading-tight">
                      {asset.name}
                    </p>
                  </div>
                </div>
                <button className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity bg-red-500 text-white rounded-full p-1">
                  <X className="w-3 h-3" />
                </button>
              </div>
            ))}
            
            {/* Upload New Asset */}
            <div className="aspect-square border-2 border-dashed border-primary-border rounded-default flex items-center justify-center hover:border-primary-accent transition-colors cursor-pointer">
              <div className="text-center">
                <Plus className="w-6 h-6 text-primary-text-secondary mx-auto mb-2" />
                <p className="text-xs text-primary-text-secondary">Add Asset</p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}