import api from './api'

// 查询请求参数
export interface QueryRequest {
  question: string
  session_id?: string
  max_tokens?: number
  relevance_threshold?: number
  template_name?: string
  enable_rerank?: boolean
  enable_optimization?: boolean
  enable_expansion?: boolean
}

// 查询响应结果
export interface QueryResponse {
  question: string
  answer: string
  query_id: string
  session_id?: string
  processing_time: number
  tokens_used: number
  relevance_score: number
  retrieved_chunks_count: number
  metadata: Record<string, unknown>
}

class QueryService {
  // 查询问答
  async query(params: QueryRequest): Promise<QueryResponse> {
    return api.post<QueryResponse>('/api/v1/query', params as unknown as Record<string, unknown>)
  }
}

export default new QueryService()
