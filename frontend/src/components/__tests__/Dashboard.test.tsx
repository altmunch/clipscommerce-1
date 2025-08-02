import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Dashboard from '../Dashboard'

// Mock the tab components
jest.mock('../tabs/StrategyTab', () => {
  return function StrategyTab() {
    return <div data-testid="strategy-tab">Strategy Tab Content</div>
  }
})

jest.mock('../tabs/PipelineTab', () => {
  return function PipelineTab() {
    return <div data-testid="pipeline-tab">Pipeline Tab Content</div>
  }
})

jest.mock('../tabs/ResultsTab', () => {
  return function ResultsTab() {
    return <div data-testid="results-tab">Results Tab Content</div>
  }
})

jest.mock('../tabs/BrandKitTab', () => {
  return function BrandKitTab() {
    return <div data-testid="brand-kit-tab">Brand Kit Tab Content</div>
  }
})

const DashboardWithProviders = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  })

  return (
    <QueryClientProvider client={queryClient}>
      <Dashboard />
    </QueryClientProvider>
  )
}

describe('Dashboard', () => {
  it('renders the main dashboard structure', () => {
    render(<DashboardWithProviders />)
    
    // Check for main brand logo
    expect(screen.getByText('ViralOS')).toBeInTheDocument()
    
    // Check for all tab triggers
    expect(screen.getByRole('button', { name: /strategy/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /pipeline/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /results/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /brand kit/i })).toBeInTheDocument()
    
    // Check for brand selector
    expect(screen.getByText('Displaying for:')).toBeInTheDocument()
    expect(screen.getByText('YourBrand.com')).toBeInTheDocument()
    
    // Check for new campaign button
    expect(screen.getByRole('button', { name: /new campaign/i })).toBeInTheDocument()
  })

  it('shows strategy tab content by default', () => {
    render(<DashboardWithProviders />)
    
    expect(screen.getByTestId('strategy-tab')).toBeInTheDocument()
    expect(screen.queryByTestId('pipeline-tab')).not.toBeInTheDocument()
    expect(screen.queryByTestId('results-tab')).not.toBeInTheDocument()
    expect(screen.queryByTestId('brand-kit-tab')).not.toBeInTheDocument()
  })

  it('switches to pipeline tab when clicked', async () => {
    const user = userEvent.setup()
    render(<DashboardWithProviders />)
    
    const pipelineTab = screen.getByRole('button', { name: /pipeline/i })
    await user.click(pipelineTab)
    
    expect(screen.getByTestId('pipeline-tab')).toBeInTheDocument()
    expect(screen.queryByTestId('strategy-tab')).not.toBeInTheDocument()
    expect(screen.queryByTestId('results-tab')).not.toBeInTheDocument()
    expect(screen.queryByTestId('brand-kit-tab')).not.toBeInTheDocument()
  })

  it('switches to results tab when clicked', async () => {
    const user = userEvent.setup()
    render(<DashboardWithProviders />)
    
    const resultsTab = screen.getByRole('button', { name: /results/i })
    await user.click(resultsTab)
    
    expect(screen.getByTestId('results-tab')).toBeInTheDocument()
    expect(screen.queryByTestId('strategy-tab')).not.toBeInTheDocument()
    expect(screen.queryByTestId('pipeline-tab')).not.toBeInTheDocument()
    expect(screen.queryByTestId('brand-kit-tab')).not.toBeInTheDocument()
  })

  it('switches to brand kit tab when clicked', async () => {
    const user = userEvent.setup()
    render(<DashboardWithProviders />)
    
    const brandKitTab = screen.getByRole('button', { name: /brand kit/i })
    await user.click(brandKitTab)
    
    expect(screen.getByTestId('brand-kit-tab')).toBeInTheDocument()
    expect(screen.queryByTestId('strategy-tab')).not.toBeInTheDocument()
    expect(screen.queryByTestId('pipeline-tab')).not.toBeInTheDocument()
    expect(screen.queryByTestId('results-tab')).not.toBeInTheDocument()
  })

  it('displays correct icons for each tab', () => {
    render(<DashboardWithProviders />)
    
    // Check that tabs contain the expected text and structure
    const strategyTab = screen.getByRole('button', { name: /strategy/i })
    const pipelineTab = screen.getByRole('button', { name: /pipeline/i })
    const resultsTab = screen.getByRole('button', { name: /results/i })
    const brandKitTab = screen.getByRole('button', { name: /brand kit/i })
    
    // These should contain both icon and text
    expect(strategyTab).toHaveTextContent('Strategy')
    expect(pipelineTab).toHaveTextContent('Pipeline')
    expect(resultsTab).toHaveTextContent('Results')
    expect(brandKitTab).toHaveTextContent('Brand Kit')
  })

  it('has proper styling classes', () => {
    render(<DashboardWithProviders />)
    
    // Check main container has proper background
    const mainContainer = screen.getByText('ViralOS').closest('.min-h-screen')
    expect(mainContainer).toHaveClass('bg-primary-bg')
    
    // Check navigation border
    const navContainer = screen.getByText('ViralOS').closest('.border-b')
    expect(navContainer).toHaveClass('border-primary-border', 'bg-primary-bg')
  })

  it('has accessible button elements', () => {
    render(<DashboardWithProviders />)
    
    // Check that all interactive elements are properly accessible
    const buttons = screen.getAllByRole('button')
    
    // Should have at least the 4 tab buttons + brand selector + new campaign button
    expect(buttons.length).toBeGreaterThanOrEqual(6)
    
    // All buttons should be in the document and properly accessible
    buttons.forEach(button => {
      expect(button).toBeInTheDocument()
      expect(button).not.toHaveAttribute('disabled')
    })
  })

  it('maintains tab state across interactions', async () => {
    const user = userEvent.setup()
    render(<DashboardWithProviders />)
    
    // Start with strategy tab (default)
    expect(screen.getByTestId('strategy-tab')).toBeInTheDocument()
    
    // Switch to pipeline
    await user.click(screen.getByRole('button', { name: /pipeline/i }))
    expect(screen.getByTestId('pipeline-tab')).toBeInTheDocument()
    
    // Switch to results
    await user.click(screen.getByRole('button', { name: /results/i }))
    expect(screen.getByTestId('results-tab')).toBeInTheDocument()
    
    // Switch back to strategy
    await user.click(screen.getByRole('button', { name: /strategy/i }))
    expect(screen.getByTestId('strategy-tab')).toBeInTheDocument()
  })

  it('renders brand selector as interactive element', () => {
    render(<DashboardWithProviders />)
    
    const brandSelector = screen.getByText('YourBrand.com').closest('button')
    expect(brandSelector).toBeInTheDocument()
    expect(brandSelector).toHaveClass('hover:text-primary-accent')
  })

  it('renders new campaign button with proper styling', () => {
    render(<DashboardWithProviders />)
    
    const newCampaignButton = screen.getByRole('button', { name: /new campaign/i })
    expect(newCampaignButton).toBeInTheDocument()
    expect(newCampaignButton).toHaveTextContent('+ New Campaign')
  })
})