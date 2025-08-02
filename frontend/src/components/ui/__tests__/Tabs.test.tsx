import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../Tabs'

describe('Tabs Components', () => {
  const TabsExample = ({ defaultValue = 'tab1' }) => (
    <Tabs defaultValue={defaultValue}>
      <TabsList>
        <TabsTrigger value="tab1">Tab 1</TabsTrigger>
        <TabsTrigger value="tab2">Tab 2</TabsTrigger>
        <TabsTrigger value="tab3">Tab 3</TabsTrigger>
      </TabsList>
      <TabsContent value="tab1">
        <div>Content for Tab 1</div>
      </TabsContent>
      <TabsContent value="tab2">
        <div>Content for Tab 2</div>
      </TabsContent>
      <TabsContent value="tab3">
        <div>Content for Tab 3</div>
      </TabsContent>
    </Tabs>
  )

  describe('Tabs', () => {
    it('renders with default value', () => {
      render(<TabsExample />)
      
      const tab1 = screen.getByRole('button', { name: /tab 1/i })
      const content1 = screen.getByText(/content for tab 1/i)
      
      expect(tab1).toHaveClass('text-primary-text', 'border-b-primary-accent')
      expect(content1).toBeInTheDocument()
    })

    it('shows only the active tab content', () => {
      render(<TabsExample />)
      
      expect(screen.getByText(/content for tab 1/i)).toBeInTheDocument()
      expect(screen.queryByText(/content for tab 2/i)).not.toBeInTheDocument()
      expect(screen.queryByText(/content for tab 3/i)).not.toBeInTheDocument()
    })

    it('accepts custom className', () => {
      render(
        <Tabs defaultValue="tab1" className="custom-tabs">
          <TabsList>
            <TabsTrigger value="tab1">Tab 1</TabsTrigger>
          </TabsList>
          <TabsContent value="tab1">Content</TabsContent>
        </Tabs>
      )
      
      const tabsContainer = screen.getByText(/tab 1/i).closest('.custom-tabs')
      expect(tabsContainer).toBeInTheDocument()
    })
  })

  describe('TabsList', () => {
    it('renders with default classes', () => {
      render(<TabsExample />)
      
      const tabsList = screen.getByRole('button', { name: /tab 1/i }).parentElement
      expect(tabsList).toHaveClass('inline-flex', 'h-12', 'items-center', 'justify-center')
    })

    it('accepts custom className', () => {
      render(
        <Tabs defaultValue="tab1">
          <TabsList className="custom-tabs-list">
            <TabsTrigger value="tab1">Tab 1</TabsTrigger>
          </TabsList>
          <TabsContent value="tab1">Content</TabsContent>
        </Tabs>
      )
      
      const tabsList = screen.getByRole('button', { name: /tab 1/i }).parentElement
      expect(tabsList).toHaveClass('custom-tabs-list')
    })
  })

  describe('TabsTrigger', () => {
    it('renders with default inactive styles', () => {
      render(<TabsExample defaultValue="tab2" />)
      
      const inactiveTab = screen.getByRole('button', { name: /tab 1/i })
      expect(inactiveTab).toHaveClass('text-primary-text-secondary', 'border-transparent')
    })

    it('renders with active styles when selected', () => {
      render(<TabsExample defaultValue="tab1" />)
      
      const activeTab = screen.getByRole('button', { name: /tab 1/i })
      expect(activeTab).toHaveClass('text-primary-text', 'border-b-primary-accent')
    })

    it('switches tabs when clicked', async () => {
      const user = userEvent.setup()
      render(<TabsExample />)
      
      // Initially tab 1 is active
      expect(screen.getByText(/content for tab 1/i)).toBeInTheDocument()
      expect(screen.queryByText(/content for tab 2/i)).not.toBeInTheDocument()
      
      // Click tab 2
      const tab2 = screen.getByRole('button', { name: /tab 2/i })
      await user.click(tab2)
      
      // Now tab 2 is active
      expect(screen.queryByText(/content for tab 1/i)).not.toBeInTheDocument()
      expect(screen.getByText(/content for tab 2/i)).toBeInTheDocument()
      
      // Tab 2 should have active styles
      expect(tab2).toHaveClass('text-primary-text', 'border-b-primary-accent')
    })

    it('updates active state correctly when switching tabs', async () => {
      const user = userEvent.setup()
      render(<TabsExample />)
      
      const tab1 = screen.getByRole('button', { name: /tab 1/i })
      const tab2 = screen.getByRole('button', { name: /tab 2/i })
      const tab3 = screen.getByRole('button', { name: /tab 3/i })
      
      // Initially tab 1 is active
      expect(tab1).toHaveClass('text-primary-text', 'border-b-primary-accent')
      expect(tab2).toHaveClass('text-primary-text-secondary', 'border-transparent')
      expect(tab3).toHaveClass('text-primary-text-secondary', 'border-transparent')
      
      // Click tab 3
      await user.click(tab3)
      
      // Now tab 3 is active, others are inactive
      expect(tab1).toHaveClass('text-primary-text-secondary', 'border-transparent')
      expect(tab2).toHaveClass('text-primary-text-secondary', 'border-transparent')
      expect(tab3).toHaveClass('text-primary-text', 'border-b-primary-accent')
    })

    it('accepts custom className', () => {
      render(
        <Tabs defaultValue="tab1">
          <TabsList>
            <TabsTrigger value="tab1" className="custom-trigger">Tab 1</TabsTrigger>
          </TabsList>
          <TabsContent value="tab1">Content</TabsContent>
        </Tabs>
      )
      
      const trigger = screen.getByRole('button', { name: /tab 1/i })
      expect(trigger).toHaveClass('custom-trigger')
    })
  })

  describe('TabsContent', () => {
    it('renders only when its value matches active tab', () => {
      render(<TabsExample />)
      
      const content1 = screen.getByText(/content for tab 1/i)
      expect(content1).toBeInTheDocument()
      expect(content1.parentElement).toHaveClass('mt-8', 'ring-offset-background')
    })

    it('does not render when its value does not match active tab', () => {
      render(<TabsExample defaultValue="tab1" />)
      
      expect(screen.queryByText(/content for tab 2/i)).not.toBeInTheDocument()
      expect(screen.queryByText(/content for tab 3/i)).not.toBeInTheDocument()
    })

    it('accepts custom className', () => {
      render(
        <Tabs defaultValue="tab1">
          <TabsList>
            <TabsTrigger value="tab1">Tab 1</TabsTrigger>
          </TabsList>
          <TabsContent value="tab1" className="custom-content">
            <div>Content</div>
          </TabsContent>
        </Tabs>
      )
      
      const content = screen.getByText(/content/i).parentElement
      expect(content).toHaveClass('custom-content')
    })
  })

  describe('Error handling', () => {
    it('throws error when TabsTrigger is used outside Tabs context', () => {
      // Suppress console.error for this test
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {})
      
      expect(() => {
        render(<TabsTrigger value="tab1">Tab 1</TabsTrigger>)
      }).toThrow('Tabs components must be used within a Tabs provider')
      
      consoleSpy.mockRestore()
    })

    it('throws error when TabsContent is used outside Tabs context', () => {
      // Suppress console.error for this test
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {})
      
      expect(() => {
        render(<TabsContent value="tab1">Content</TabsContent>)
      }).toThrow('Tabs components must be used within a Tabs provider')
      
      consoleSpy.mockRestore()
    })
  })

  describe('Accessibility', () => {
    it('has proper focus styles', () => {
      render(<TabsExample />)
      
      const tab = screen.getByRole('button', { name: /tab 1/i })
      expect(tab).toHaveClass('focus-visible:outline-none', 'focus-visible:ring-2')
    })

    it('supports keyboard navigation', async () => {
      const user = userEvent.setup()
      render(<TabsExample />)
      
      const tab1 = screen.getByRole('button', { name: /tab 1/i })
      
      // Focus the first tab
      await user.tab()
      expect(tab1).toHaveFocus()
    })
  })
})