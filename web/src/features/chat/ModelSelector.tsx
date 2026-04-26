import { useCallback, useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Check, ChevronDown, ChevronRight, Cpu, Loader2 } from 'lucide-react'
import type { ModelGroup } from './chatApi'
import { useModelStore } from './modelStore'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'

export default function ModelSelector() {
  const { t } = useTranslation()
  const [groups, setGroups] = useState<ModelGroup[]>([])
  const [loading, setLoading] = useState(true)
  const [open, setOpen] = useState(false)
  const [expanded, setExpanded] = useState<Set<string>>(new Set())
  const selectedModel = useModelStore((s) => s.selectedModel)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    let active = true
    fetch(`${API_BASE}/api/v1/models`)
      .then((r) => r.json())
      .then((data: { groups: ModelGroup[]; default: string }) => {
        if (!active) { return }
        setGroups(data.groups)
        setLoading(false)

        const cur = useModelStore.getState().selectedModel
        const allIds = data.groups.flatMap((g) => g.models)
        if (!cur || !allIds.includes(cur)) {
          useModelStore.getState().setModel(data.default || allIds[0] || '')
        }

        // 自动展开选中模型所在的组
        const sel = cur || data.default
        const ownerGroup = data.groups.find((g) => g.models.includes(sel))
        if (ownerGroup) {
          setExpanded(new Set([ownerGroup.key]))
        }
      })
      .catch((err) => {
        if (!active) { return }
        console.error('fetch models failed:', err)
        setLoading(false)
      })
    return () => { active = false }
  }, [])

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const toggleGroup = useCallback((key: string) => {
    setExpanded((prev) => {
      const next = new Set(prev)
      if (next.has(key)) {
        next.delete(key)
      } else {
        next.add(key)
      }
      return next
    })
  }, [])

  const pick = useCallback((id: string) => {
    useModelStore.getState().setModel(id)
    setOpen(false)
  }, [])

  if (loading) {
    return (
      <div className="flex items-center gap-1.5 rounded-full border border-stone-200 bg-white px-3 py-1.5 text-xs text-stone-400 dark:border-stone-600 dark:bg-stone-800 dark:text-stone-500">
        <Loader2 size={13} className="animate-spin" />
        <span>{t('loadingModels')}</span>
      </div>
    )
  }

  if (groups.length === 0) {
    return (
      <div className="rounded-full border border-red-200 bg-red-50 px-3 py-1.5 text-xs text-red-500 dark:border-red-800 dark:bg-red-900/30">
        {t('noModels')}
      </div>
    )
  }

  return (
    <div ref={containerRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 rounded-full border border-stone-200 bg-white px-3 py-1.5 text-xs font-medium text-stone-700 shadow-sm transition hover:border-stone-300 hover:shadow dark:border-stone-600 dark:bg-stone-800 dark:text-stone-200 dark:hover:border-stone-500"
      >
        <Cpu size={13} className="text-stone-400 dark:text-stone-500" />
        <span className="max-w-[140px] truncate">{selectedModel || 'Select model'}</span>
        <ChevronDown
          size={12}
          className={`text-stone-400 transition-transform duration-200 ${open ? 'rotate-180' : ''}`}
        />
      </button>

      {open && (
        <div className="absolute left-0 top-full z-50 mt-1.5 max-h-[420px] min-w-[240px] overflow-y-auto overscroll-contain rounded-xl border border-stone-200 bg-white py-1 shadow-xl dark:border-stone-600 dark:bg-stone-800">
          {groups.map((group) => {
            const isExpanded = expanded.has(group.key)
            const hasSelected = group.models.includes(selectedModel)

            return (
              <div key={group.key}>
                <button
                  type="button"
                  onClick={() => toggleGroup(group.key)}
                  className={`flex w-full items-center gap-1.5 px-3 py-2 text-left text-[11px] font-semibold transition ${
                    hasSelected
                      ? 'text-stone-900 dark:text-white'
                      : 'text-stone-500 hover:text-stone-700 dark:text-stone-400 dark:hover:text-stone-200'
                  }`}
                >
                  {isExpanded
                    ? <ChevronDown size={12} />
                    : <ChevronRight size={12} />
                  }
                  <span className="flex-1">{group.label}</span>
                  <span className="text-[10px] font-normal text-stone-400 dark:text-stone-500">
                    {group.models.length}
                  </span>
                </button>

                {isExpanded && (
                  <div className="pb-1">
                    {group.models.map((id) => (
                      <button
                        key={id}
                        type="button"
                        onClick={() => pick(id)}
                        className={`flex w-full items-center gap-2 py-1.5 pl-8 pr-3 text-left text-xs transition ${
                          id === selectedModel
                            ? 'bg-stone-100 font-medium text-stone-900 dark:bg-stone-700 dark:text-white'
                            : 'text-stone-500 hover:bg-stone-50 hover:text-stone-700 dark:text-stone-400 dark:hover:bg-stone-700/50 dark:hover:text-stone-200'
                        }`}
                      >
                        <span className="flex-1 truncate">{id}</span>
                        {id === selectedModel && (
                          <Check size={13} className="shrink-0 text-emerald-500" />
                        )}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
