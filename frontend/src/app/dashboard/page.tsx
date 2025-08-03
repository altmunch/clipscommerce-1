"use client";

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Dashboard from "@/components/Dashboard";

export default function DashboardPage() {
  const router = useRouter();
  const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null);

  useEffect(() => {
    // Check if user is authenticated (only on client side)
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('accessToken');
      
      if (!token) {
        router.push('/auth/login');
        setIsAuthenticated(false);
      } else {
        setIsAuthenticated(true);
      }
    }
  }, [router]);

  // Show loading while checking authentication
  if (isAuthenticated === null) {
    return (
      <div className="min-h-screen bg-primary-bg flex items-center justify-center">
        <div className="text-primary-text">Loading...</div>
      </div>
    );
  }

  // If not authenticated, show redirecting message
  if (isAuthenticated === false) {
    return (
      <div className="min-h-screen bg-primary-bg flex items-center justify-center">
        <div className="text-primary-text">Redirecting to login...</div>
      </div>
    );
  }

  return <Dashboard />;
}