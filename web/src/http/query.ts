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

// 导入状态响应
export interface ImportStatusResponse {
  service_initialized: boolean
  milvus_connected: boolean
  embedding_available: boolean
}

// 导入结果响应
export interface ImportResponse {
  success: boolean
  message: string
  data_dir?: string
  dataset_name?: string
  files_processed?: number
  data_created?: number
  vectors_created?: number
  error?: string
}

class QueryService {
  // 查询问答
  async query(params: QueryRequest): Promise<QueryResponse> {
    return api.post<QueryResponse>('/query/', params as unknown as Record<string, unknown>)
  }

  // 获取导入状态
  async getImportStatus(): Promise<ImportStatusResponse> {
    return api.get<ImportStatusResponse>('/api/import/status')
  }

  // 启动数据导入
  async startImport(dataDir = './data', datasetName = '文档知识库'): Promise<ImportResponse> {
    return api.post<ImportResponse>('/api/import/start', {
      data_dir: dataDir,
      dataset_name: datasetName,
    })
  }

  // 同步执行数据导入
  async importSync(dataDir = './data', datasetName = '文档知识库'): Promise<ImportResponse> {
    return api.post<ImportResponse>('/api/import/import-sync', {
      data_dir: dataDir,
      dataset_name: datasetName,
    })
  }
}

export default new QueryService()
