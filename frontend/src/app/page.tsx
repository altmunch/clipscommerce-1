"use client";

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function Home() {
  const router = useRouter();

  useEffect(() => {
    // Check if user is authenticated
    const token = localStorage.getItem('accessToken');
    
    if (token) {
      // User is logged in, redirect to dashboard
      router.push('/dashboard');
    } else {
      // User is not logged in, redirect to landing page
      router.push('/landing');
    }
  }, [router]);

  // Show loading state while redirecting
  return (
    <div className="min-h-screen bg-primary-bg flex items-center justify-center">
      <div className="text-primary-text">Loading...</div>
    </div>
  );
}