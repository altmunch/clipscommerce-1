"use client";

import { useState, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Button } from '@/components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { ChevronLeft, Mail, Lock, User } from 'lucide-react';
import Link from 'next/link';
import { useApi } from '@/hooks/useApi';

function SignupPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const plan = searchParams?.get('plan') || 'starter';
  
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    confirmPassword: ''
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isLoading, setIsLoading] = useState(false);

  const { post } = useApi();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrors({});
    
    // Validation
    if (!formData.email) {
      setErrors(prev => ({ ...prev, email: 'Email is required' }));
      return;
    }
    if (!formData.password || formData.password.length < 8) {
      setErrors(prev => ({ ...prev, password: 'Password must be at least 8 characters' }));
      return;
    }
    if (formData.password !== formData.confirmPassword) {
      setErrors(prev => ({ ...prev, confirmPassword: 'Passwords do not match' }));
      return;
    }

    setIsLoading(true);
    
    try {
      await post('/auth/register', {
        email: formData.email,
        password: formData.password
      });
      
      // Redirect to login with success message
      router.push(`/auth/login?email=${encodeURIComponent(formData.email)}&plan=${plan}&signup=success`);
    } catch (error: any) {
      setErrors({ general: error.response?.data?.detail || 'Registration failed' });
    } finally {
      setIsLoading(false);
    }
  };

  const planDisplayNames: Record<string, string> = {
    starter: 'Starter Plan ($249/mo)',
    autonomous: 'Autonomous Plan ($749/mo)',
    enterprise: 'Enterprise Plan (Custom)'
  };

  return (
    <div className="min-h-screen bg-primary-bg flex items-center justify-center px-6">
      <div className="w-full max-w-md">
        {/* Back to Landing */}
        <div className="mb-8">
          <Link href="/landing" className="flex items-center text-primary-text-secondary hover:text-primary-text transition-colors">
            <ChevronLeft className="w-4 h-4 mr-2" />
            Back to Landing Page
          </Link>
        </div>

        <Card className="border-primary-border bg-primary-card">
          <CardHeader className="text-center pb-8">
            <CardTitle className="text-2xl font-bold text-primary-text mb-2">
              Start Your Growth Journey
            </CardTitle>
            <p className="text-primary-text-secondary">
              Create your ViralOS account for {planDisplayNames[plan]}
            </p>
          </CardHeader>
          
          <CardContent className="space-y-6">
            {errors.general && (
              <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-lg">
                <p className="text-red-400 text-sm">{errors.general}</p>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-primary-text mb-2">
                  Email Address
                </label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-primary-text-secondary" />
                  <input
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData(prev => ({ ...prev, email: e.target.value }))}
                    className="w-full pl-10 pr-4 py-3 bg-primary-bg border border-primary-border rounded-lg text-primary-text placeholder-primary-text-secondary focus:outline-none focus:ring-2 focus:ring-primary-accent focus:border-transparent"
                    placeholder="founder@yourbrand.com"
                    required
                  />
                </div>
                {errors.email && <p className="text-red-400 text-sm mt-1">{errors.email}</p>}
              </div>

              <div>
                <label className="block text-sm font-medium text-primary-text mb-2">
                  Password
                </label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-primary-text-secondary" />
                  <input
                    type="password"
                    value={formData.password}
                    onChange={(e) => setFormData(prev => ({ ...prev, password: e.target.value }))}
                    className="w-full pl-10 pr-4 py-3 bg-primary-bg border border-primary-border rounded-lg text-primary-text placeholder-primary-text-secondary focus:outline-none focus:ring-2 focus:ring-primary-accent focus:border-transparent"
                    placeholder="Minimum 8 characters"
                    required
                  />
                </div>
                {errors.password && <p className="text-red-400 text-sm mt-1">{errors.password}</p>}
              </div>

              <div>
                <label className="block text-sm font-medium text-primary-text mb-2">
                  Confirm Password
                </label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-primary-text-secondary" />
                  <input
                    type="password"
                    value={formData.confirmPassword}
                    onChange={(e) => setFormData(prev => ({ ...prev, confirmPassword: e.target.value }))}
                    className="w-full pl-10 pr-4 py-3 bg-primary-bg border border-primary-border rounded-lg text-primary-text placeholder-primary-text-secondary focus:outline-none focus:ring-2 focus:ring-primary-accent focus:border-transparent"
                    placeholder="Confirm your password"
                    required
                  />
                </div>
                {errors.confirmPassword && <p className="text-red-400 text-sm mt-1">{errors.confirmPassword}</p>}
              </div>

              <Button 
                type="submit" 
                className="w-full py-3 bg-gradient-to-r from-primary-accent to-chart-pink hover:opacity-90"
                disabled={isLoading}
              >
                {isLoading ? 'Creating Account...' : 'Create Account'}
              </Button>
            </form>

            <div className="pt-6 border-t border-primary-border text-center">
              <p className="text-primary-text-secondary">
                Already have an account?{' '}
                <Link href={`/auth/login?plan=${plan}`} className="text-primary-accent hover:underline">
                  Sign in
                </Link>
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Plan Info */}
        <div className="mt-6 text-center">
          <p className="text-sm text-primary-text-secondary">
            You're signing up for the <span className="text-primary-accent font-medium">{planDisplayNames[plan]}</span>
          </p>
        </div>
      </div>
    </div>
  );
}

export default function SignupPage() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <SignupPageContent />
    </Suspense>
  );
}