import api from './axios'

export interface ApiResponse<T = unknown> {
  code: number
  message: string
  data: T
}

class ApiService {
  // GET 请求
  async get<T = unknown>(url: string, params?: Record<string, unknown>): Promise<T> {
    return api.get(url, { params })
  }

  // POST 请求
  async post<T = unknown>(url: string, data?: Record<string, unknown>): Promise<T> {
    return api.post(url, data)
  }

  // PUT 请求
  async put<T = unknown>(url: string, data?: Record<string, unknown>): Promise<T> {
    return api.put(url, data)
  }

  // DELETE 请求
  async delete<T = unknown>(url: string): Promise<T> {
    return api.delete(url)
  }

  // PATCH 请求
  async patch<T = unknown>(url: string, data?: Record<string, unknown>): Promise<T> {
    return api.patch(url, data)
  }

  // 文件上传
  async upload<T = unknown>(url: string, file: File, onProgress?: (progress: number) => void): Promise<T> {
    const formData = new FormData()
    formData.append('file', file)

    return api.post(url, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (progressEvent.total && onProgress) {
          const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total)
          onProgress(progress)
        }
      },
    })
  }
}

export default new ApiService() 