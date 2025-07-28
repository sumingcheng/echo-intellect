import axios, { type AxiosError, type AxiosResponse } from 'axios'

// 创建 axios 实例
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    // 可以在这里添加 token
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }

    console.log('请求发送:', config)
    return config
  },
  (error) => {
    console.error('请求错误:', error)
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  (response: AxiosResponse) => {
    console.log('响应接收:', response)
    return response.data
  },
  (error: AxiosError) => {
    console.error('响应错误:', error)

    // 统一错误处理
    if (error.response?.status === 401) {
      // 未授权，清除 token 并跳转到登录页
      localStorage.removeItem('token')
      window.location.href = '/login'
    }

    return Promise.reject(error)
  }
)

export default api 