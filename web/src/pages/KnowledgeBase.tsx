import React, { useState, useEffect, useCallback } from 'react';
import { RiRefreshLine, RiUploadLine, RiCheckLine, RiCloseLine, RiErrorWarningLine, RiArrowLeftLine } from 'react-icons/ri';
import { Link } from 'react-router-dom';
import queryService, { type ImportStatusResponse, type ImportResponse } from '@/http/query';
import { ScrollArea } from '@/components/ui/scroll-area';
import toast from 'react-hot-toast';

export default function KnowledgeBase() {
  const [status, setStatus] = useState<ImportStatusResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState<ImportResponse | null>(null);
  const [statusError, setStatusError] = useState(false);

  // 获取导入状态
  const fetchStatus = useCallback(async () => {
    setLoading(true);
    setStatusError(false);
    try {
      const response = await queryService.getImportStatus();
      setStatus(response);
    } catch (error) {
      console.error('获取状态失败:', error);
      toast.error('获取状态失败');
      // 设置失败状态
      setStatusError(true);
      setStatus({
        service_initialized: false,
        milvus_connected: false,
        embedding_available: false,
      });
    } finally {
      setLoading(false);
    }
  }, []);

  // 启动数据导入 (异步)
  const handleAsyncImport = useCallback(async () => {
    setImporting(true);
    setImportResult(null);
    try {
      const response = await queryService.startImport();
      setImportResult(response);
      if (response.success) {
        toast.success('异步导入已启动');
        // 导入完成后刷新状态
        await fetchStatus();
      } else {
        toast.error(response.message || '导入失败');
      }
    } catch (error) {
      console.error('导入失败:', error);
      toast.error('导入失败');
      setImportResult({
        success: false,
        message: '导入过程中出现错误',
        error: String(error),
      });
    } finally {
      setImporting(false);
    }
  }, [fetchStatus]);

  // 同步执行数据导入
  const handleSyncImport = useCallback(async () => {
    setImporting(true);
    setImportResult(null);
    try {
      const response = await queryService.importSync();
      setImportResult(response);
      if (response.success) {
        toast.success('同步导入完成');
        // 导入完成后刷新状态
        await fetchStatus();
      } else {
        toast.error(response.message || '导入失败');
      }
    } catch (error) {
      console.error('导入失败:', error);
      toast.error('导入失败');
      setImportResult({
        success: false,
        message: '导入过程中出现错误',
        error: String(error),
      });
    } finally {
      setImporting(false);
    }
  }, [fetchStatus]);

  // 初始化时获取状态
  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  // 状态指示器组件
  const StatusIndicator = ({ label, value, icon }: { label: string; value: boolean; icon: React.ReactElement }) => (
    <div className="flex items-center justify-between p-3 rounded-lg border border-gray-200">
      <div className="flex items-center gap-3">
        {icon}
        <span className="text-sm font-medium text-gray-700">{label}</span>
      </div>
      <div className={`flex items-center gap-2 px-2 py-1 rounded-full text-xs font-medium ${value ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
        {value ? <RiCheckLine className="h-3 w-3" /> : <RiCloseLine className="h-3 w-3" />}
        {value ? '正常' : '异常'}
      </div>
    </div>
  );

  return (
    <div className="h-screen bg-white flex flex-col">
      {/* 顶部导航 */}
      <div className="border-b border-gray-200 bg-white px-6 py-4">
        <div className="flex items-center justify-between max-w-4xl mx-auto">
          <div className="flex items-center gap-4">
            <Link to="/" className="p-2 rounded-lg hover:bg-gray-100 transition-colors" title="返回聊天">
              <RiArrowLeftLine className="h-4 w-4 text-gray-600" />
            </Link>
            <div>
              <h1 className="text-lg font-semibold text-gray-900">知识库管理</h1>
              <p className="text-sm text-gray-500">管理和导入文档数据到知识库</p>
            </div>
          </div>
        </div>
      </div>

      {/* 主内容区域 */}
      <div className="flex-1 overflow-hidden">
        <ScrollArea className="h-full">
          <div className="mx-auto max-w-4xl px-6 py-6">
            <div className="space-y-6">
              {/* 系统状态 */}
              <div className="bg-gray-50 rounded-xl p-6">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-lg font-semibold text-gray-900">系统状态</h2>
                  <button
                    onClick={fetchStatus}
                    disabled={loading}
                    className="flex items-center gap-2 px-3 py-2 text-sm bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    <RiRefreshLine className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
                    刷新状态
                  </button>
                </div>

                {loading && !status ? (
                  <div className="text-center py-8">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
                    <p className="text-sm text-gray-600 mt-2">获取状态中...</p>
                  </div>
                ) : status ? (
                  <div className="space-y-3">
                    {statusError && (
                      <div className="flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-lg">
                        <RiErrorWarningLine className="h-5 w-5 text-red-500" />
                        <span className="text-sm text-red-700 font-medium">连接失败 - 以下为最后已知状态</span>
                      </div>
                    )}
                    <div className="grid gap-3">
                      <StatusIndicator label="服务初始化" value={status.service_initialized} icon={<RiCheckLine className="h-5 w-5 text-blue-600" />} />
                      <StatusIndicator label="Milvus 连接" value={status.milvus_connected} icon={<RiCheckLine className="h-5 w-5 text-green-600" />} />
                      <StatusIndicator label="向量模型" value={status.embedding_available} icon={<RiCheckLine className="h-5 w-5 text-purple-600" />} />
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-8">
                    <RiErrorWarningLine className="h-8 w-8 text-red-400 mx-auto mb-2" />
                    <p className="text-sm text-gray-600">获取状态失败</p>
                  </div>
                )}
              </div>

              {/* 数据导入 */}
              <div className="bg-gray-50 rounded-xl p-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">数据导入</h2>

                <div className="bg-white rounded-lg border border-gray-200 p-4 mb-4">
                  <div className="flex items-start gap-3">
                    <RiUploadLine className="h-5 w-5 text-blue-600 mt-0.5" />
                    <div className="flex-1">
                      <h3 className="text-sm font-medium text-gray-900">导入本地文档</h3>
                      <p className="text-sm text-gray-600 mt-1">
                        从 <code className="bg-gray-100 px-1 rounded">./data</code> 目录导入文档到 <code className="bg-gray-100 px-1 rounded">文档知识库</code>
                      </p>
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <button
                    onClick={handleAsyncImport}
                    disabled={importing || !status?.service_initialized}
                    className="flex items-center justify-center gap-2 px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    {importing ? (
                      <>
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                        导入中...
                      </>
                    ) : (
                      <>
                        <RiUploadLine className="h-4 w-4" />
                        异步导入
                      </>
                    )}
                  </button>

                  <button
                    onClick={handleSyncImport}
                    disabled={importing || !status?.service_initialized}
                    className="flex items-center justify-center gap-2 px-4 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    {importing ? (
                      <>
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                        导入中...
                      </>
                    ) : (
                      <>
                        <RiUploadLine className="h-4 w-4" />
                        同步导入
                      </>
                    )}
                  </button>
                </div>

                {!status?.service_initialized && <p className="text-sm text-red-600 mt-2 text-center">服务未初始化，无法进行导入</p>}
              </div>

              {/* 导入结果 */}
              {importResult && (
                <div className="bg-gray-50 rounded-xl p-6">
                  <h2 className="text-lg font-semibold text-gray-900 mb-4">导入结果</h2>

                  <div className={`p-4 rounded-lg border ${importResult.success ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'}`}>
                    <div className="flex items-start gap-3">
                      {importResult.success ? <RiCheckLine className="h-5 w-5 text-green-600 mt-0.5" /> : <RiCloseLine className="h-5 w-5 text-red-600 mt-0.5" />}
                      <div className="flex-1">
                        <h3 className={`text-sm font-medium ${importResult.success ? 'text-green-900' : 'text-red-900'}`}>{importResult.success ? '导入成功' : '导入失败'}</h3>
                        <p className={`text-sm mt-1 ${importResult.success ? 'text-green-700' : 'text-red-700'}`}>{importResult.message}</p>

                        {importResult.success && (
                          <div className="mt-3 grid grid-cols-2 gap-4 text-sm">
                            {importResult.files_processed && (
                              <div>
                                <span className="text-green-600 font-medium">处理文件：</span>
                                <span className="text-green-700">{importResult.files_processed} 个</span>
                              </div>
                            )}
                            {importResult.data_created && (
                              <div>
                                <span className="text-green-600 font-medium">创建数据：</span>
                                <span className="text-green-700">{importResult.data_created} 条</span>
                              </div>
                            )}
                            {importResult.vectors_created && (
                              <div>
                                <span className="text-green-600 font-medium">生成向量：</span>
                                <span className="text-green-700">{importResult.vectors_created} 个</span>
                              </div>
                            )}
                            {importResult.dataset_name && (
                              <div>
                                <span className="text-green-600 font-medium">数据集：</span>
                                <span className="text-green-700">{importResult.dataset_name}</span>
                              </div>
                            )}
                          </div>
                        )}

                        {!importResult.success && importResult.error && <div className="mt-2 p-2 bg-red-100 rounded text-xs text-red-800 font-mono">{importResult.error}</div>}
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </ScrollArea>
      </div>
    </div>
  );
}
