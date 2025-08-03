"use client";

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { brandApi, campaignApi, contentApi, resultsApi, jobApi } from '@/lib/api';

// Brand hooks
export function useBrands() {
  return useQuery({
    queryKey: ['brands'],
    queryFn: () => brandApi.getBrands().then(res => res.data),
  });
}

export function useBrandKit(brandId: string) {
  return useQuery({
    queryKey: ['brandKit', brandId],
    queryFn: () => brandApi.getBrandKit(brandId).then(res => res.data),
    enabled: !!brandId,
  });
}

export function useAssimilateBrand() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (url: string) => brandApi.assimilate(url).then(res => res.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['brands'] });
    },
  });
}

export function useUpdateBrandKit() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ brandId, data }: { brandId: string; data: any }) =>
      brandApi.updateBrandKit(brandId, data).then(res => res.data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['brandKit', variables.brandId] });
    },
  });
}

// Campaign hooks
export function useCampaigns(brandId: string) {
  return useQuery({
    queryKey: ['campaigns', brandId],
    queryFn: () => campaignApi.getByCampaigns(brandId).then(res => res.data),
    enabled: !!brandId,
  });
}

export function useCreateCampaign() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: any) => campaignApi.create(data).then(res => res.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaigns'] });
    },
  });
}

// Content hooks
export function useIdeas(brandId: string) {
  return useQuery({
    queryKey: ['ideas', brandId],
    queryFn: () => contentApi.getIdeas(brandId).then(res => res.data),
    enabled: !!brandId,
  });
}

export function useGenerateIdeas() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ brandId, campaignId }: { brandId: string; campaignId?: string }) =>
      contentApi.generateIdeas(brandId, campaignId).then(res => res.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ideas'] });
    },
  });
}

export function useGenerateBlueprint() {
  return useMutation({
    mutationFn: (ideaId: string) => contentApi.generateBlueprint(ideaId).then(res => res.data),
  });
}

export function useGenerateVideo() {
  return useMutation({
    mutationFn: (blueprintId: string) => contentApi.generateVideo(blueprintId).then(res => res.data),
  });
}

export function useOptimizeVideo() {
  return useMutation({
    mutationFn: ({ videoId, data }: { videoId: string; data: any }) =>
      contentApi.optimizeVideo(videoId, data).then(res => res.data),
  });
}

export function useScheduleVideo() {
  return useMutation({
    mutationFn: ({ videoId, data }: { videoId: string; data: any }) =>
      contentApi.scheduleVideo(videoId, data).then(res => res.data),
  });
}

// Results hooks
export function useKpis(brandId: string, startDate?: string, endDate?: string) {
  return useQuery({
    queryKey: ['kpis', brandId, startDate, endDate],
    queryFn: () => resultsApi.getKpis(brandId, startDate, endDate).then(res => res.data),
    enabled: !!brandId,
  });
}

export function useChartData(brandId: string, metric: string, startDate?: string, endDate?: string) {
  return useQuery({
    queryKey: ['chart', brandId, metric, startDate, endDate],
    queryFn: () => resultsApi.getChart(brandId, metric, startDate, endDate).then(res => res.data),
    enabled: !!brandId && !!metric,
  });
}

export function useContentPerformance(brandId: string, sortBy?: string, page?: number) {
  return useQuery({
    queryKey: ['contentPerformance', brandId, sortBy, page],
    queryFn: () => resultsApi.getContent(brandId, sortBy, page).then(res => res.data),
    enabled: !!brandId,
  });
}

export function useInsights(brandId: string) {
  return useQuery({
    queryKey: ['insights', brandId],
    queryFn: () => resultsApi.getInsights(brandId).then(res => res.data),
    enabled: !!brandId,
  });
}

// Job hooks
export function useJobStatus(jobId: string, enabled: boolean = true) {
  return useQuery({
    queryKey: ['jobStatus', jobId],
    queryFn: () => jobApi.getStatus(jobId).then(res => res.data),
    enabled: !!jobId && enabled,
    refetchInterval: (query) => {
      // Stop polling when job is complete or failed
      if (query.state.data?.status === 'complete' || query.state.data?.status === 'failed') {
        return false;
      }
      return 2000; // Poll every 2 seconds
    },
  });
}

// Generic API hook for auth pages
export function useApi() {
  return {
    post: async (endpoint: string, data: any) => {
      const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      });
      
      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw { response: { data: error } };
      }
      
      return { data: await response.json() };
    }
  };
}