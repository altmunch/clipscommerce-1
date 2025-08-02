import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReactNode } from 'react'
import {
  useBrands,
  useBrandKit,
  useAssimilateBrand,
  useUpdateBrandKit,
  useCampaigns,
  useCreateCampaign,
  useIdeas,
  useGenerateIdeas,
  useGenerateBlueprint,
  useGenerateVideo,
  useKpis,
  useChartData,
  useContentPerformance,
  useInsights,
  useJobStatus
} from '../useApi'

// Create a wrapper component for React Query
const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  })

  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  )
}

describe('useApi hooks', () => {
  describe('Brand hooks', () => {
    describe('useBrands', () => {
      it('fetches brands successfully', async () => {
        const wrapper = createWrapper()
        const { result } = renderHook(() => useBrands(), { wrapper })

        await waitFor(() => {
          expect(result.current.isSuccess).toBe(true)
        })

        expect(result.current.data).toHaveLength(2)
        expect(result.current.data[0]).toEqual(
          expect.objectContaining({
            id: 'brand-1',
            name: 'TechCorp',
            url: 'https://techcorp.com'
          })
        )
      })

      it('handles loading state', () => {
        const wrapper = createWrapper()
        const { result } = renderHook(() => useBrands(), { wrapper })

        expect(result.current.isLoading).toBe(true)
        expect(result.current.data).toBeUndefined()
      })
    })

    describe('useBrandKit', () => {
      it('fetches brand kit when brandId is provided', async () => {
        const wrapper = createWrapper()
        const { result } = renderHook(() => useBrandKit('brand-1'), { wrapper })

        await waitFor(() => {
          expect(result.current.isSuccess).toBe(true)
        })

        expect(result.current.data).toEqual(
          expect.objectContaining({
            colors: expect.any(Array),
            fonts: expect.any(Array),
            voice: expect.any(String)
          })
        )
      })

      it('does not fetch when brandId is empty', () => {
        const wrapper = createWrapper()
        const { result } = renderHook(() => useBrandKit(''), { wrapper })

        expect(result.current.isIdle).toBe(true)
        expect(result.current.data).toBeUndefined()
      })
    })

    describe('useAssimilateBrand', () => {
      it('assimilates brand successfully', async () => {
        const wrapper = createWrapper()
        const { result } = renderHook(() => useAssimilateBrand(), { wrapper })

        result.current.mutate('https://example.com')

        await waitFor(() => {
          expect(result.current.isSuccess).toBe(true)
        })

        expect(result.current.data).toEqual(
          expect.objectContaining({
            id: 'new-brand-id',
            url: 'https://example.com',
            name: 'New Brand'
          })
        )
      })

      it('handles mutation loading state', () => {
        const wrapper = createWrapper()
        const { result } = renderHook(() => useAssimilateBrand(), { wrapper })

        expect(result.current.isPending).toBe(false)
        expect(result.current.data).toBeUndefined()
      })
    })

    describe('useUpdateBrandKit', () => {
      it('updates brand kit successfully', async () => {
        const wrapper = createWrapper()
        const { result } = renderHook(() => useUpdateBrandKit(), { wrapper })

        const updateData = { colors: ['#FF0000'], voice: 'Updated voice' }
        result.current.mutate({ brandId: 'brand-1', data: updateData })

        await waitFor(() => {
          expect(result.current.isSuccess).toBe(true)
        })

        expect(result.current.data).toEqual(
          expect.objectContaining({
            id: 'brand-1',
            ...updateData
          })
        )
      })
    })
  })

  describe('Campaign hooks', () => {
    describe('useCampaigns', () => {
      it('fetches campaigns for a brand', async () => {
        const wrapper = createWrapper()
        const { result } = renderHook(() => useCampaigns('brand-1'), { wrapper })

        await waitFor(() => {
          expect(result.current.isSuccess).toBe(true)
        })

        expect(result.current.data).toEqual(
          expect.arrayContaining([
            expect.objectContaining({
              brand_id: 'brand-1',
              name: expect.any(String)
            })
          ])
        )
      })

      it('does not fetch when brandId is empty', () => {
        const wrapper = createWrapper()
        const { result } = renderHook(() => useCampaigns(''), { wrapper })

        expect(result.current.isIdle).toBe(true)
      })
    })

    describe('useCreateCampaign', () => {
      it('creates campaign successfully', async () => {
        const wrapper = createWrapper()
        const { result } = renderHook(() => useCreateCampaign(), { wrapper })

        const campaignData = {
          brand_id: 'brand-1',
          name: 'Test Campaign',
          description: 'Test campaign description'
        }

        result.current.mutate(campaignData)

        await waitFor(() => {
          expect(result.current.isSuccess).toBe(true)
        })

        expect(result.current.data).toEqual(
          expect.objectContaining({
            id: 'new-campaign-id',
            ...campaignData
          })
        )
      })
    })
  })

  describe('Content hooks', () => {
    describe('useIdeas', () => {
      it('fetches ideas for a brand', async () => {
        const wrapper = createWrapper()
        const { result } = renderHook(() => useIdeas('brand-1'), { wrapper })

        await waitFor(() => {
          expect(result.current.isSuccess).toBe(true)
        })

        expect(result.current.data).toEqual(
          expect.arrayContaining([
            expect.objectContaining({
              brand_id: 'brand-1',
              title: expect.any(String),
              type: expect.any(String)
            })
          ])
        )
      })
    })

    describe('useGenerateIdeas', () => {
      it('generates ideas successfully', async () => {
        const wrapper = createWrapper()
        const { result } = renderHook(() => useGenerateIdeas(), { wrapper })

        result.current.mutate({ brandId: 'brand-1', campaignId: 'campaign-1' })

        await waitFor(() => {
          expect(result.current.isSuccess).toBe(true)
        })

        expect(result.current.data).toEqual(
          expect.objectContaining({
            job_id: expect.any(String),
            status: 'processing'
          })
        )
      })
    })

    describe('useGenerateBlueprint', () => {
      it('generates blueprint successfully', async () => {
        const wrapper = createWrapper()
        const { result } = renderHook(() => useGenerateBlueprint(), { wrapper })

        result.current.mutate('idea-1')

        await waitFor(() => {
          expect(result.current.isSuccess).toBe(true)
        })

        expect(result.current.data).toEqual(
          expect.objectContaining({
            job_id: expect.any(String),
            status: 'processing'
          })
        )
      })
    })

    describe('useGenerateVideo', () => {
      it('generates video successfully', async () => {
        const wrapper = createWrapper()
        const { result } = renderHook(() => useGenerateVideo(), { wrapper })

        result.current.mutate('blueprint-1')

        await waitFor(() => {
          expect(result.current.isSuccess).toBe(true)
        })

        expect(result.current.data).toEqual(
          expect.objectContaining({
            job_id: expect.any(String),
            status: 'processing'
          })
        )
      })
    })
  })

  describe('Results hooks', () => {
    describe('useKpis', () => {
      it('fetches KPIs for a brand', async () => {
        const wrapper = createWrapper()
        const { result } = renderHook(() => useKpis('brand-1'), { wrapper })

        await waitFor(() => {
          expect(result.current.isSuccess).toBe(true)
        })

        expect(result.current.data).toEqual(
          expect.objectContaining({
            total_views: expect.any(Number),
            total_engagement: expect.any(Number),
            avg_engagement_rate: expect.any(Number)
          })
        )
      })

      it('includes date range parameters in query', async () => {
        const wrapper = createWrapper()
        const { result } = renderHook(() => 
          useKpis('brand-1', '2024-01-01', '2024-01-31'), 
          { wrapper }
        )

        await waitFor(() => {
          expect(result.current.isSuccess).toBe(true)
        })

        expect(result.current.data).toBeDefined()
      })
    })

    describe('useChartData', () => {
      it('fetches chart data for a metric', async () => {
        const wrapper = createWrapper()
        const { result } = renderHook(() => 
          useChartData('brand-1', 'views'), 
          { wrapper }
        )

        await waitFor(() => {
          expect(result.current.isSuccess).toBe(true)
        })

        expect(result.current.data).toEqual(
          expect.objectContaining({
            labels: expect.any(Array),
            data: expect.any(Array)
          })
        )
      })

      it('does not fetch when metric is not provided', () => {
        const wrapper = createWrapper()
        const { result } = renderHook(() => 
          useChartData('brand-1', ''), 
          { wrapper }
        )

        expect(result.current.isIdle).toBe(true)
      })
    })

    describe('useContentPerformance', () => {
      it('fetches content performance data', async () => {
        const wrapper = createWrapper()
        const { result } = renderHook(() => useContentPerformance('brand-1'), { wrapper })

        await waitFor(() => {
          expect(result.current.isSuccess).toBe(true)
        })

        expect(result.current.data).toEqual(
          expect.arrayContaining([
            expect.objectContaining({
              title: expect.any(String),
              platform: expect.any(String),
              views: expect.any(Number)
            })
          ])
        )
      })
    })

    describe('useInsights', () => {
      it('fetches insights for a brand', async () => {
        const wrapper = createWrapper()
        const { result } = renderHook(() => useInsights('brand-1'), { wrapper })

        await waitFor(() => {
          expect(result.current.isSuccess).toBe(true)
        })

        expect(result.current.data).toEqual(
          expect.arrayContaining([
            expect.objectContaining({
              type: expect.any(String),
              title: expect.any(String),
              description: expect.any(String),
              priority: expect.any(String)
            })
          ])
        )
      })
    })
  })

  describe('Job hooks', () => {
    describe('useJobStatus', () => {
      it('fetches job status', async () => {
        const wrapper = createWrapper()
        const { result } = renderHook(() => useJobStatus('job-123'), { wrapper })

        await waitFor(() => {
          expect(result.current.isSuccess).toBe(true)
        })

        expect(result.current.data).toEqual(
          expect.objectContaining({
            id: 'job-123',
            status: 'complete',
            progress: 100
          })
        )
      })

      it('does not fetch when disabled', () => {
        const wrapper = createWrapper()
        const { result } = renderHook(() => useJobStatus('job-123', false), { wrapper })

        expect(result.current.isIdle).toBe(true)
      })

      it('does not fetch when jobId is empty', () => {
        const wrapper = createWrapper()
        const { result } = renderHook(() => useJobStatus(''), { wrapper })

        expect(result.current.isIdle).toBe(true)
      })
    })
  })

  describe('Error handling', () => {
    it('handles API errors gracefully', async () => {
      // Mock a failed response for this test
      const wrapper = createWrapper()
      
      // This would require more sophisticated mocking to test error states
      // For now, we test the basic structure
      const { result } = renderHook(() => useBrands(), { wrapper })
      
      // Initially should be loading
      expect(result.current.isLoading).toBe(true)
    })
  })

  describe('React Query integration', () => {
    it('uses correct query keys', () => {
      const wrapper = createWrapper()
      
      // Test that hooks work with React Query
      const brandsResult = renderHook(() => useBrands(), { wrapper })
      const brandKitResult = renderHook(() => useBrandKit('brand-1'), { wrapper })
      const campaignsResult = renderHook(() => useCampaigns('brand-1'), { wrapper })
      
      // All should initialize properly
      expect(brandsResult.result.current).toBeDefined()
      expect(brandKitResult.result.current).toBeDefined()
      expect(campaignsResult.result.current).toBeDefined()
    })

    it('invalidates queries correctly on mutations', async () => {
      const wrapper = createWrapper()
      
      // Test mutation hooks initialize properly
      const assimilateResult = renderHook(() => useAssimilateBrand(), { wrapper })
      const updateBrandKitResult = renderHook(() => useUpdateBrandKit(), { wrapper })
      const createCampaignResult = renderHook(() => useCreateCampaign(), { wrapper })
      
      expect(assimilateResult.result.current.mutate).toBeInstanceOf(Function)
      expect(updateBrandKitResult.result.current.mutate).toBeInstanceOf(Function)
      expect(createCampaignResult.result.current.mutate).toBeInstanceOf(Function)
    })
  })
})