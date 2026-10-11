const API_BASE = '/api';

async function request(url: string, options?: RequestInit) {
  const headers: Record<string, string> = { ...(options?.headers as Record<string, string> | undefined) };
  if (options?.body !== undefined) headers['Content-Type'] = 'application/json';
  const response = await fetch(`${API_BASE}${url}`, { ...options, headers });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }
  return response.json();
}

export const api = {
  health: () => request('/health'),

  loadDemo: () => request('/demo/load', { method: 'POST' }),

  uploadSource: async (file?: File, text?: string, url?: string) => {
    const formData = new FormData();
    if (file) formData.append('file', file);
    if (text) formData.append('text', text);
    if (url) formData.append('url', url);
    const res = await fetch(`${API_BASE}/sources/upload`, { method: 'POST', body: formData });
    if (!res.ok) {
      const error = await res.json().catch(() => ({ detail: 'Upload failed' }));
      throw new Error(error.detail || 'Upload failed');
    }
    return res.json();
  },

  getSource: (id: number) => request(`/sources/${id}`),

  analyzeSource: (sourceId: number) =>
    request('/sources/analyze', { method: 'POST', body: JSON.stringify({ source_id: sourceId }) }),

  getContentDna: (sourceId: number) => request(`/content-dna/${sourceId}`),

  getClaims: (sourceId: number) => request(`/claims/${sourceId}`),

  getKnowledgeMap: (sourceId: number) => request(`/knowledge-map/${sourceId}`),

  transform: (data: {
    source_id: number;
    output_formats?: string[];
    output_format: string;
    audience: string;
    knowledge_level: string;
    tone: string;
    length?: 'short' | 'medium' | 'detailed';
  }) => request('/transform', { method: 'POST', body: JSON.stringify(data) }),

  getTransformation: (id: number) => request(`/transform/${id}`),

  getTransformations: (sourceId?: number) => request(`/transformations${sourceId ? `?source_id=${sourceId}` : ''}`),

  getSourceChunks: (id: number) => request(`/sources/${id}/chunks`),

  getSourceStructure: (id: number) => request(`/sources/${id}/structure`),

  verifyTransformation: (id: number) =>
    request(`/transform/${id}/verify`, { method: 'POST' }),

  auditTransformation: (id: number) =>
    request(`/transform/${id}/audit`, { method: 'POST' }),

  regenerateTransformation: (id: number) =>
    request(`/transform/${id}/regenerate`, { method: 'POST' }),

  generateVariations: (data: {
    source_id: number;
    output_format: string;
    audience: string;
    knowledge_level: string;
    tone: string;
  }) => request('/transform/variations', { method: 'POST', body: JSON.stringify(data) }),

  chat: (message: string, transformationId?: number, currentOutput?: string) =>
    request('/chat', {
      method: 'POST',
      body: JSON.stringify({ message, transformation_id: transformationId, current_output: currentOutput }),
    }),

  getProjects: () => request('/projects'),
  createProject: (name: string, sourceId?: number) =>
    request('/projects', { method: 'POST', body: JSON.stringify({ name, source_id: sourceId }) }),

  exportContent: (content: string, format: string, filename: string, metadata?: any) =>
    request('/export', {
      method: 'POST',
      body: JSON.stringify({ content, format, filename, metadata }),
    }),

  getAnalytics: () => request('/analytics'),
};
