import { render, screen } from '@testing-library/react'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../Card'

describe('Card Components', () => {
  describe('Card', () => {
    it('renders with default classes', () => {
      render(<Card data-testid="card">Card content</Card>)
      
      const card = screen.getByTestId('card')
      expect(card).toBeInTheDocument()
      expect(card).toHaveClass('rounded-default', 'bg-primary-card', 'p-6', 'shadow-sm')
    })

    it('accepts custom className', () => {
      render(<Card className="custom-class" data-testid="card">Card content</Card>)
      
      const card = screen.getByTestId('card')
      expect(card).toHaveClass('custom-class')
    })

    it('forwards ref correctly', () => {
      const ref = jest.fn()
      render(<Card ref={ref}>Card content</Card>)
      
      expect(ref).toHaveBeenCalledWith(expect.any(HTMLDivElement))
    })

    it('spreads additional props', () => {
      render(<Card data-testid="card" role="region">Card content</Card>)
      
      const card = screen.getByTestId('card')
      expect(card).toHaveAttribute('role', 'region')
    })
  })

  describe('CardHeader', () => {
    it('renders with default classes', () => {
      render(<CardHeader data-testid="card-header">Header content</CardHeader>)
      
      const header = screen.getByTestId('card-header')
      expect(header).toBeInTheDocument()
      expect(header).toHaveClass('flex', 'flex-col', 'space-y-1.5', 'pb-4')
    })

    it('accepts custom className', () => {
      render(<CardHeader className="custom-header" data-testid="card-header">Header</CardHeader>)
      
      const header = screen.getByTestId('card-header')
      expect(header).toHaveClass('custom-header')
    })

    it('forwards ref correctly', () => {
      const ref = jest.fn()
      render(<CardHeader ref={ref}>Header content</CardHeader>)
      
      expect(ref).toHaveBeenCalledWith(expect.any(HTMLDivElement))
    })
  })

  describe('CardTitle', () => {
    it('renders as h3 element with default classes', () => {
      render(<CardTitle>Card Title</CardTitle>)
      
      const title = screen.getByRole('heading', { level: 3 })
      expect(title).toBeInTheDocument()
      expect(title).toHaveClass('font-semibold', 'text-primary-text', 'leading-none', 'tracking-tight')
      expect(title).toHaveTextContent('Card Title')
    })

    it('accepts custom className', () => {
      render(<CardTitle className="custom-title">Title</CardTitle>)
      
      const title = screen.getByRole('heading', { level: 3 })
      expect(title).toHaveClass('custom-title')
    })

    it('forwards ref correctly', () => {
      const ref = jest.fn()
      render(<CardTitle ref={ref}>Title</CardTitle>)
      
      expect(ref).toHaveBeenCalledWith(expect.any(HTMLHeadingElement))
    })
  })

  describe('CardDescription', () => {
    it('renders with default classes', () => {
      render(<CardDescription data-testid="card-description">Description text</CardDescription>)
      
      const description = screen.getByTestId('card-description')
      expect(description).toBeInTheDocument()
      expect(description).toHaveClass('text-sm', 'text-primary-text-secondary')
      expect(description).toHaveTextContent('Description text')
    })

    it('accepts custom className', () => {
      render(<CardDescription className="custom-desc" data-testid="card-description">Desc</CardDescription>)
      
      const description = screen.getByTestId('card-description')
      expect(description).toHaveClass('custom-desc')
    })

    it('forwards ref correctly', () => {
      const ref = jest.fn()
      render(<CardDescription ref={ref}>Description</CardDescription>)
      
      expect(ref).toHaveBeenCalledWith(expect.any(HTMLParagraphElement))
    })
  })

  describe('CardContent', () => {
    it('renders with minimal default styling', () => {
      render(<CardContent data-testid="card-content">Content</CardContent>)
      
      const content = screen.getByTestId('card-content')
      expect(content).toBeInTheDocument()
      expect(content).toHaveTextContent('Content')
    })

    it('accepts custom className', () => {
      render(<CardContent className="custom-content" data-testid="card-content">Content</CardContent>)
      
      const content = screen.getByTestId('card-content')
      expect(content).toHaveClass('custom-content')
    })

    it('forwards ref correctly', () => {
      const ref = jest.fn()
      render(<CardContent ref={ref}>Content</CardContent>)
      
      expect(ref).toHaveBeenCalledWith(expect.any(HTMLDivElement))
    })
  })

  describe('Card composition', () => {
    it('renders complete card structure', () => {
      render(
        <Card data-testid="full-card">
          <CardHeader>
            <CardTitle>Test Card</CardTitle>
            <CardDescription>This is a test card description</CardDescription>
          </CardHeader>
          <CardContent>
            <p>Card content goes here</p>
          </CardContent>
        </Card>
      )
      
      const card = screen.getByTestId('full-card')
      const title = screen.getByRole('heading', { name: /test card/i })
      const description = screen.getByText(/this is a test card description/i)
      const content = screen.getByText(/card content goes here/i)
      
      expect(card).toBeInTheDocument()
      expect(title).toBeInTheDocument()
      expect(description).toBeInTheDocument()
      expect(content).toBeInTheDocument()
    })
  })
})