import { http, HttpResponse } from 'msw'
import { mockBrands, mockCampaigns, mockContent, mockKpis, mockInsights } from './mockData'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

export const handlers = [
  // Brand endpoints
  http.get(`${API_BASE_URL}/brands`, () => {
    return HttpResponse.json(mockBrands)
  }),

  http.get(`${API_BASE_URL}/brands/:id/kit`, ({ params }) => {
    const brandId = params.id as string
    const brand = mockBrands.find(b => b.id === brandId)
    if (!brand) {
      return new HttpResponse(null, { status: 404 })
    }
    return HttpResponse.json(brand.brandKit)
  }),

  http.post(`${API_BASE_URL}/brands/assimilate`, async ({ request }) => {
    const body = await request.json() as { url: string }
    return HttpResponse.json({
      id: 'new-brand-id',
      url: body.url,
      name: 'New Brand',
      status: 'processing'
    })
  }),

  http.put(`${API_BASE_URL}/brands/:id/kit`, async ({ params, request }) => {
    const brandId = params.id as string
    const body = await request.json()
    return HttpResponse.json({
      id: brandId,
      ...body,
      updated_at: new Date().toISOString()
    })
  }),

  // Campaign endpoints
  http.get(`${API_BASE_URL}/campaigns`, ({ request }) => {
    const url = new URL(request.url)
    const brandId = url.searchParams.get('brand_id')
    return HttpResponse.json(mockCampaigns.filter(c => c.brand_id === brandId))
  }),

  http.post(`${API_BASE_URL}/campaigns`, async ({ request }) => {
    const body = await request.json()
    return HttpResponse.json({
      id: 'new-campaign-id',
      ...body,
      created_at: new Date().toISOString()
    })
  }),

  // Content endpoints
  http.get(`${API_BASE_URL}/content/ideas`, ({ request }) => {
    const url = new URL(request.url)
    const brandId = url.searchParams.get('brand_id')
    return HttpResponse.json(mockContent.ideas.filter(i => i.brand_id === brandId))
  }),

  http.post(`${API_BASE_URL}/content/ideas/generate`, async ({ request }) => {
    const body = await request.json() as { brand_id: string; campaign_id?: string }
    return HttpResponse.json({
      job_id: 'job-123',
      status: 'processing',
      message: 'Generating ideas...'
    })
  }),

  http.post(`${API_BASE_URL}/content/blueprint/:ideaId`, ({ params }) => {
    return HttpResponse.json({
      job_id: 'job-456',
      status: 'processing',
      message: 'Generating blueprint...'
    })
  }),

  http.post(`${API_BASE_URL}/content/video/:blueprintId`, ({ params }) => {
    return HttpResponse.json({
      job_id: 'job-789',
      status: 'processing',
      message: 'Generating video...'
    })
  }),

  // Results endpoints
  http.get(`${API_BASE_URL}/results/kpis`, ({ request }) => {
    const url = new URL(request.url)
    const brandId = url.searchParams.get('brand_id')
    return HttpResponse.json(mockKpis)
  }),

  http.get(`${API_BASE_URL}/results/chart`, ({ request }) => {
    const url = new URL(request.url)
    const metric = url.searchParams.get('metric')
    return HttpResponse.json({
      labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May'],
      data: [100, 150, 200, 180, 250]
    })
  }),

  http.get(`${API_BASE_URL}/results/content`, ({ request }) => {
    const url = new URL(request.url)
    const brandId = url.searchParams.get('brand_id')
    return HttpResponse.json(mockContent.performance)
  }),

  http.get(`${API_BASE_URL}/results/insights`, ({ request }) => {
    const url = new URL(request.url)
    const brandId = url.searchParams.get('brand_id')
    return HttpResponse.json(mockInsights)
  }),

  // Job endpoints
  http.get(`${API_BASE_URL}/jobs/:id/status`, ({ params }) => {
    const jobId = params.id as string
    return HttpResponse.json({
      id: jobId,
      status: 'complete',
      progress: 100,
      result: { message: 'Job completed successfully' }
    })
  }),

  // Auth endpoints
  http.post(`${API_BASE_URL}/auth/login`, async ({ request }) => {
    const body = await request.json() as { email: string; password: string }
    return HttpResponse.json({
      access_token: 'mock-jwt-token',
      token_type: 'bearer',
      user: {
        id: 'user-1',
        email: body.email,
        name: 'Test User'
      }
    })
  }),

  http.post(`${API_BASE_URL}/auth/logout`, () => {
    return HttpResponse.json({ message: 'Logged out successfully' })
  }),
]