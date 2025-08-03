/**
 * Comprehensive tests for brand workflow components including
 * URL analysis, product discovery, video generation, and social posting.
 */

import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { rest } from 'msw'
import { setupServer } from 'msw/node'
import BrandWorkflow from '../BrandWorkflow'
import { mockData } from '../../__mocks__/mockData'

// Mock server for API calls
const server = setupServer(
  rest.post('/api/v1/brands/:brandId/analyze-url', (req, res, ctx) => {
    return res(ctx.json(mockData.brandAnalysis))
  }),
  
  rest.post('/api/v1/video-generation/projects', (req, res, ctx) => {
    return res(ctx.json(mockData.videoProject))
  }),
  
  rest.post('/api/v1/social-media/post-multi-platform', (req, res, ctx) => {
    return res(ctx.json(mockData.socialMediaPost))
  }),
  
  rest.get('/api/v1/jobs/:jobId/status', (req, res, ctx) => {
    return res(ctx.json(mockData.jobStatus))
  })
)

beforeAll(() => server.listen())
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false }
    }
  })

  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  )
}

describe('BrandWorkflow', () => {
  describe('URL Analysis Phase', () => {
    it('starts URL analysis when URL is submitted', async () => {
      const user = userEvent.setup()
      render(<BrandWorkflow />, { wrapper: createWrapper() })

      const urlInput = screen.getByPlaceholderText(/enter brand url/i)
      const analyzeButton = screen.getByRole('button', { name: /analyze brand/i })

      await user.type(urlInput, 'https://example-brand.com')
      await user.click(analyzeButton)

      expect(screen.getByText(/analyzing brand/i)).toBeInTheDocument()
    })

    it('displays validation error for invalid URLs', async () => {
      const user = userEvent.setup()
      render(<BrandWorkflow />, { wrapper: createWrapper() })

      const urlInput = screen.getByPlaceholderText(/enter brand url/i)
      const analyzeButton = screen.getByRole('button', { name: /analyze brand/i })

      await user.type(urlInput, 'not-a-valid-url')
      await user.click(analyzeButton)

      expect(screen.getByText(/please enter a valid url/i)).toBeInTheDocument()
    })

    it('shows progress during brand analysis', async () => {
      const user = userEvent.setup()
      render(<BrandWorkflow />, { wrapper: createWrapper() })

      const urlInput = screen.getByPlaceholderText(/enter brand url/i)
      const analyzeButton = screen.getByRole('button', { name: /analyze brand/i })

      await user.type(urlInput, 'https://example-brand.com')
      await user.click(analyzeButton)

      // Check for loading indicators
      expect(screen.getByRole('progressbar')).toBeInTheDocument()
      expect(screen.getByText(/extracting brand information/i)).toBeInTheDocument()
    })

    it('displays analysis results after completion', async () => {
      const user = userEvent.setup()
      render(<BrandWorkflow />, { wrapper: createWrapper() })

      const urlInput = screen.getByPlaceholderText(/enter brand url/i)
      const analyzeButton = screen.getByRole('button', { name: /analyze brand/i })

      await user.type(urlInput, 'https://example-brand.com')
      await user.click(analyzeButton)

      await waitFor(() => {
        expect(screen.getByText(mockData.brandAnalysis.brand_info.name)).toBeInTheDocument()
      })

      expect(screen.getByText(/products discovered/i)).toBeInTheDocument()
      expect(screen.getByText(mockData.brandAnalysis.products.length.toString())).toBeInTheDocument()
    })
  })

  describe('Video Generation Phase', () => {
    it('allows proceeding to video generation after analysis', async () => {
      const user = userEvent.setup()
      render(<BrandWorkflow />, { wrapper: createWrapper() })

      // Complete brand analysis first
      const urlInput = screen.getByPlaceholderText(/enter brand url/i)
      const analyzeButton = screen.getByRole('button', { name: /analyze brand/i })

      await user.type(urlInput, 'https://example-brand.com')
      await user.click(analyzeButton)

      await waitFor(() => {
        expect(screen.getByText(mockData.brandAnalysis.brand_info.name)).toBeInTheDocument()
      })

      // Proceed to video generation
      const generateVideoButton = screen.getByRole('button', { name: /generate video/i })
      await user.click(generateVideoButton)

      expect(screen.getByText(/video generation/i)).toBeInTheDocument()
    })

    it('displays video generation configuration options', async () => {
      const user = userEvent.setup()
      render(<BrandWorkflow />, { wrapper: createWrapper() })

      // Navigate to video generation phase
      await navigateToVideoGeneration(user)

      expect(screen.getByLabelText(/target platform/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/video duration/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/video style/i)).toBeInTheDocument()
    })

    it('starts video generation with selected options', async () => {
      const user = userEvent.setup()
      render(<BrandWorkflow />, { wrapper: createWrapper() })

      await navigateToVideoGeneration(user)

      // Configure video options
      const platformSelect = screen.getByLabelText(/target platform/i)
      const durationSlider = screen.getByLabelText(/video duration/i)
      const startGenerationButton = screen.getByRole('button', { name: /start generation/i })

      await user.selectOptions(platformSelect, 'tiktok')
      fireEvent.change(durationSlider, { target: { value: '30' } })
      await user.click(startGenerationButton)

      expect(screen.getByText(/generating video/i)).toBeInTheDocument()
    })

    it('shows real-time progress during video generation', async () => {
      const user = userEvent.setup()
      render(<BrandWorkflow />, { wrapper: createWrapper() })

      await navigateToVideoGeneration(user)
      await startVideoGeneration(user)

      // Check for progress indicators
      expect(screen.getByRole('progressbar')).toBeInTheDocument()
      expect(screen.getByText(/script generation/i)).toBeInTheDocument()
    })

    it('displays generated video preview when complete', async () => {
      const user = userEvent.setup()
      render(<BrandWorkflow />, { wrapper: createWrapper() })

      await navigateToVideoGeneration(user)
      await startVideoGeneration(user)

      await waitFor(() => {
        expect(screen.getByText(/video generated successfully/i)).toBeInTheDocument()
      })

      expect(screen.getByRole('video')).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /download video/i })).toBeInTheDocument()
    })
  })

  describe('Social Media Posting Phase', () => {
    it('allows proceeding to social media posting after video generation', async () => {
      const user = userEvent.setup()
      render(<BrandWorkflow />, { wrapper: createWrapper() })

      await navigateToSocialPosting(user)

      expect(screen.getByText(/social media posting/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/select platforms/i)).toBeInTheDocument()
    })

    it('displays platform-specific options', async () => {
      const user = userEvent.setup()
      render(<BrandWorkflow />, { wrapper: createWrapper() })

      await navigateToSocialPosting(user)

      // Select TikTok
      const tiktokCheckbox = screen.getByLabelText(/tiktok/i)
      await user.click(tiktokCheckbox)

      expect(screen.getByPlaceholderText(/tiktok caption/i)).toBeInTheDocument()
      expect(screen.getByPlaceholderText(/tiktok hashtags/i)).toBeInTheDocument()

      // Select Instagram
      const instagramCheckbox = screen.getByLabelText(/instagram/i)
      await user.click(instagramCheckbox)

      expect(screen.getByPlaceholderText(/instagram caption/i)).toBeInTheDocument()
    })

    it('posts to selected social media platforms', async () => {
      const user = userEvent.setup()
      render(<BrandWorkflow />, { wrapper: createWrapper() })

      await navigateToSocialPosting(user)

      // Configure posting
      const tiktokCheckbox = screen.getByLabelText(/tiktok/i)
      const captionInput = screen.getByPlaceholderText(/tiktok caption/i)
      const postButton = screen.getByRole('button', { name: /post to platforms/i })

      await user.click(tiktokCheckbox)
      await user.type(captionInput, 'Check out our amazing product! #viral')
      await user.click(postButton)

      expect(screen.getByText(/posting to platforms/i)).toBeInTheDocument()
    })

    it('displays posting results and platform links', async () => {
      const user = userEvent.setup()
      render(<BrandWorkflow />, { wrapper: createWrapper() })

      await navigateToSocialPosting(user)
      await executePosting(user)

      await waitFor(() => {
        expect(screen.getByText(/posted successfully/i)).toBeInTheDocument()
      })

      expect(screen.getByText(/view on tiktok/i)).toBeInTheDocument()
      expect(screen.getByRole('link', { name: /view on tiktok/i })).toBeInTheDocument()
    })
  })

  describe('Error Handling', () => {
    it('handles network errors gracefully', async () => {
      server.use(
        rest.post('/api/v1/brands/:brandId/analyze-url', (req, res, ctx) => {
          return res(ctx.status(500), ctx.json({ error: 'Server error' }))
        })
      )

      const user = userEvent.setup()
      render(<BrandWorkflow />, { wrapper: createWrapper() })

      const urlInput = screen.getByPlaceholderText(/enter brand url/i)
      const analyzeButton = screen.getByRole('button', { name: /analyze brand/i })

      await user.type(urlInput, 'https://example-brand.com')
      await user.click(analyzeButton)

      await waitFor(() => {
        expect(screen.getByText(/something went wrong/i)).toBeInTheDocument()
      })

      expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument()
    })

    it('allows retrying failed operations', async () => {
      let callCount = 0
      server.use(
        rest.post('/api/v1/brands/:brandId/analyze-url', (req, res, ctx) => {
          callCount++
          if (callCount === 1) {
            return res(ctx.status(500), ctx.json({ error: 'Server error' }))
          }
          return res(ctx.json(mockData.brandAnalysis))
        })
      )

      const user = userEvent.setup()
      render(<BrandWorkflow />, { wrapper: createWrapper() })

      const urlInput = screen.getByPlaceholderText(/enter brand url/i)
      const analyzeButton = screen.getByRole('button', { name: /analyze brand/i })

      await user.type(urlInput, 'https://example-brand.com')
      await user.click(analyzeButton)

      await waitFor(() => {
        expect(screen.getByText(/something went wrong/i)).toBeInTheDocument()
      })

      // Retry
      const retryButton = screen.getByRole('button', { name: /try again/i })
      await user.click(retryButton)

      await waitFor(() => {
        expect(screen.getByText(mockData.brandAnalysis.brand_info.name)).toBeInTheDocument()
      })
    })

    it('validates form inputs before submission', async () => {
      const user = userEvent.setup()
      render(<BrandWorkflow />, { wrapper: createWrapper() })

      await navigateToVideoGeneration(user)

      // Try to start generation without required fields
      const startGenerationButton = screen.getByRole('button', { name: /start generation/i })
      await user.click(startGenerationButton)

      expect(screen.getByText(/please configure all required options/i)).toBeInTheDocument()
    })
  })

  describe('Accessibility', () => {
    it('provides proper ARIA labels and roles', () => {
      render(<BrandWorkflow />, { wrapper: createWrapper() })

      expect(screen.getByRole('main')).toHaveAttribute('aria-label', 'Brand Workflow')
      expect(screen.getByRole('progressbar')).toHaveAttribute('aria-label', 'Workflow Progress')
    })

    it('supports keyboard navigation', async () => {
      const user = userEvent.setup()
      render(<BrandWorkflow />, { wrapper: createWrapper() })

      const urlInput = screen.getByPlaceholderText(/enter brand url/i)
      const analyzeButton = screen.getByRole('button', { name: /analyze brand/i })

      // Tab navigation
      await user.tab()
      expect(urlInput).toHaveFocus()

      await user.tab()
      expect(analyzeButton).toHaveFocus()

      // Enter key activation
      await user.type(urlInput, 'https://example-brand.com')
      analyzeButton.focus()
      await user.keyboard('{Enter}')

      expect(screen.getByText(/analyzing brand/i)).toBeInTheDocument()
    })

    it('announces status changes to screen readers', async () => {
      const user = userEvent.setup()
      render(<BrandWorkflow />, { wrapper: createWrapper() })

      const urlInput = screen.getByPlaceholderText(/enter brand url/i)
      const analyzeButton = screen.getByRole('button', { name: /analyze brand/i })

      await user.type(urlInput, 'https://example-brand.com')
      await user.click(analyzeButton)

      const statusRegion = screen.getByRole('status')
      expect(statusRegion).toHaveTextContent(/analyzing brand/i)
    })
  })

  describe('Performance', () => {
    it('does not re-render unnecessarily', () => {
      const renderSpy = jest.fn()
      const TestComponent = () => {
        renderSpy()
        return <BrandWorkflow />
      }

      const { rerender } = render(<TestComponent />, { wrapper: createWrapper() })
      
      expect(renderSpy).toHaveBeenCalledTimes(1)

      rerender(<TestComponent />)
      expect(renderSpy).toHaveBeenCalledTimes(1) // Should not re-render with same props
    })

    it('lazy loads video player component', async () => {
      const user = userEvent.setup()
      render(<BrandWorkflow />, { wrapper: createWrapper() })

      // Video player should not be in DOM initially
      expect(screen.queryByRole('video')).not.toBeInTheDocument()

      await navigateToVideoGeneration(user)
      await startVideoGeneration(user)

      await waitFor(() => {
        expect(screen.getByRole('video')).toBeInTheDocument()
      })
    })
  })
})

// Helper functions
async function navigateToVideoGeneration(user: any) {
  const urlInput = screen.getByPlaceholderText(/enter brand url/i)
  const analyzeButton = screen.getByRole('button', { name: /analyze brand/i })

  await user.type(urlInput, 'https://example-brand.com')
  await user.click(analyzeButton)

  await waitFor(() => {
    expect(screen.getByText(mockData.brandAnalysis.brand_info.name)).toBeInTheDocument()
  })

  const generateVideoButton = screen.getByRole('button', { name: /generate video/i })
  await user.click(generateVideoButton)
}

async function startVideoGeneration(user: any) {
  const platformSelect = screen.getByLabelText(/target platform/i)
  const startGenerationButton = screen.getByRole('button', { name: /start generation/i })

  await user.selectOptions(platformSelect, 'tiktok')
  await user.click(startGenerationButton)
}

async function navigateToSocialPosting(user: any) {
  await navigateToVideoGeneration(user)
  await startVideoGeneration(user)

  await waitFor(() => {
    expect(screen.getByText(/video generated successfully/i)).toBeInTheDocument()
  })

  const proceedToPostingButton = screen.getByRole('button', { name: /proceed to posting/i })
  await user.click(proceedToPostingButton)
}

async function executePosting(user: any) {
  const tiktokCheckbox = screen.getByLabelText(/tiktok/i)
  const captionInput = screen.getByPlaceholderText(/tiktok caption/i)
  const postButton = screen.getByRole('button', { name: /post to platforms/i })

  await user.click(tiktokCheckbox)
  await user.type(captionInput, 'Check out our amazing product! #viral')
  await user.click(postButton)
}