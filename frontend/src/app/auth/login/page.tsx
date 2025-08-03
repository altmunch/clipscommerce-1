"use client";

import { useState, useEffect, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Button } from '@/components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { ChevronLeft, Mail, Lock, CheckCircle } from 'lucide-react';
import Link from 'next/link';
import { useApi } from '@/hooks/useApi';

function LoginPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const email = searchParams?.get('email') || '';
  const plan = searchParams?.get('plan') || 'starter';
  const signupSuccess = searchParams?.get('signup') === 'success';
  
  const [formData, setFormData] = useState({
    email: email,
    password: ''
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isLoading, setIsLoading] = useState(false);

  const { post } = useApi();

  useEffect(() => {
    if (email) {
      setFormData(prev => ({ ...prev, email }));
    }
  }, [email]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrors({});
    
    if (!formData.email || !formData.password) {
      setErrors({ general: 'Email and password are required' });
      return;
    }

    setIsLoading(true);
    
    try {
      const response = await post('/auth/login', {
        email: formData.email,
        password: formData.password
      });
      
      // Store token in localStorage (or you could use cookies)
      localStorage.setItem('accessToken', response.data.accessToken);
      
      // Redirect to dashboard
      router.push('/dashboard');
    } catch (error: any) {
      setErrors({ general: error.response?.data?.detail || 'Login failed' });
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

        {/* Success Message */}
        {signupSuccess && (
          <div className="mb-6 p-4 bg-green-500/10 border border-green-500/20 rounded-lg flex items-center space-x-3">
            <CheckCircle className="w-5 h-5 text-green-400" />
            <p className="text-green-400">Account created successfully! Please sign in to continue.</p>
          </div>
        )}

        <Card className="border-primary-border bg-primary-card">
          <CardHeader className="text-center pb-8">
            <CardTitle className="text-2xl font-bold text-primary-text mb-2">
              Welcome Back
            </CardTitle>
            <p className="text-primary-text-secondary">
              Sign in to your ViralOS dashboard
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
                    placeholder="Your password"
                    required
                  />
                </div>
              </div>

              <div className="flex items-center justify-between">
                <label className="flex items-center">
                  <input type="checkbox" className="rounded border-primary-border text-primary-accent focus:ring-primary-accent" />
                  <span className="ml-2 text-sm text-primary-text-secondary">Remember me</span>
                </label>
                <Link href="/auth/forgot-password" className="text-sm text-primary-accent hover:underline">
                  Forgot password?
                </Link>
              </div>

              <Button 
                type="submit" 
                className="w-full py-3 bg-gradient-to-r from-primary-accent to-chart-pink hover:opacity-90"
                disabled={isLoading}
              >
                {isLoading ? 'Signing In...' : 'Sign In'}
              </Button>
            </form>

            <div className="pt-6 border-t border-primary-border text-center">
              <p className="text-primary-text-secondary">
                Don't have an account?{' '}
                <Link href={`/auth/signup?plan=${plan}`} className="text-primary-accent hover:underline">
                  Sign up
                </Link>
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Plan Info */}
        {plan && (
          <div className="mt-6 text-center">
            <p className="text-sm text-primary-text-secondary">
              Ready to start with the <span className="text-primary-accent font-medium">{planDisplayNames[plan]}</span>
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <LoginPageContent />
    </Suspense>
  );
}