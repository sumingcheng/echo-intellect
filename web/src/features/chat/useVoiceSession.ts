import { useCallback, useRef, useState } from 'react'
import i18n from '@/i18n'
import {
  sendChatMessage,
  synthesizeSpeech,
  transcribeAudio,
  type ChatResponse,
} from './chatApi'
import { useModelStore } from './modelStore'
import type { VoiceSessionError, VoiceSessionStatus } from './voiceTypes'

interface UseVoiceSessionOptions {
  ensureSession: () => string
  onUserMessage: (sessionId: string, text: string) => void
  onAssistantMessage: (sessionId: string, response: ChatResponse) => void
}

const VOICE_THRESHOLD = 0.045
const SILENCE_THRESHOLD = 0.02
const SILENCE_MS = 1600
const MIN_AUDIO_BYTES = 1200

function pickMimeType(): string | undefined {
  return ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4'].find((type) =>
    MediaRecorder.isTypeSupported(type),
  )
}

function getVolume(analyser: AnalyserNode, data: Uint8Array): number {
  analyser.getByteTimeDomainData(data)
  let sum = 0
  for (const value of data) {
    const normalized = (value - 128) / 128
    sum += normalized * normalized
  }
  return Math.sqrt(sum / data.length)
}

export function useVoiceSession({
  ensureSession,
  onUserMessage,
  onAssistantMessage,
}: UseVoiceSessionOptions) {
  const [status, setStatus] = useState<VoiceSessionStatus>('inactive')
  const [transcript, setTranscript] = useState('')
  const [error, setError] = useState<VoiceSessionError | null>(null)

  const statusRef = useRef<VoiceSessionStatus>('inactive')
  const streamRef = useRef<MediaStream | null>(null)
  const audioContextRef = useRef<AudioContext | null>(null)
  const analyserRef = useRef<AnalyserNode | null>(null)
  const dataRef = useRef<Uint8Array | null>(null)
  const recorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<BlobPart[]>([])
  const silenceStartedAtRef = useRef<number | null>(null)
  const animationFrameRef = useRef<number | null>(null)
  const playerRef = useRef<HTMLAudioElement | null>(null)
  const playerUrlRef = useRef<string | null>(null)
  const resolvePlaybackRef = useRef<(() => void) | null>(null)
  const cancelledRef = useRef(false)

  const updateStatus = useCallback((nextStatus: VoiceSessionStatus) => {
    statusRef.current = nextStatus
    setStatus(nextStatus)
  }, [])

  const cleanupPlayer = useCallback(() => {
    playerRef.current?.pause()
    playerRef.current = null
    if (playerUrlRef.current) {
      URL.revokeObjectURL(playerUrlRef.current)
      playerUrlRef.current = null
    }
    resolvePlaybackRef.current?.()
    resolvePlaybackRef.current = null
  }, [])

  const stopMonitoring = useCallback(() => {
    if (animationFrameRef.current !== null) {
      cancelAnimationFrame(animationFrameRef.current)
      animationFrameRef.current = null
    }
  }, [])

  const cleanupAudio = useCallback(() => {
    stopMonitoring()
    streamRef.current?.getTracks().forEach((track) => track.stop())
    streamRef.current = null
    void audioContextRef.current?.close()
    audioContextRef.current = null
    analyserRef.current = null
    dataRef.current = null
    recorderRef.current = null
    chunksRef.current = []
    silenceStartedAtRef.current = null
  }, [stopMonitoring])

  const playAudio = useCallback(
    async (response: ChatResponse) => {
      if (!response.speech || cancelledRef.current) {
        return
      }

      updateStatus('speaking')
      const audio = await synthesizeSpeech({
        text: response.speech.text,
        voice: response.speech.voice,
        response_format: response.speech.response_format,
      })

      if (cancelledRef.current) {
        return
      }

      cleanupPlayer()
      const url = URL.createObjectURL(audio)
      const player = new Audio(url)
      playerRef.current = player
      playerUrlRef.current = url

      await new Promise<void>((resolve, reject) => {
        resolvePlaybackRef.current = resolve
        player.onended = () => {
          cleanupPlayer()
          resolve()
        }
        player.onerror = () => {
          cleanupPlayer()
          reject(new Error(i18n.t('voicePlaybackFailed')))
        }
        void player.play().catch(reject)
      })
    },
    [cleanupPlayer, updateStatus],
  )

  const processUtterance = useCallback(
    async (blob: Blob) => {
      if (cancelledRef.current) {
        return
      }

      if (blob.size < MIN_AUDIO_BYTES) {
        updateStatus('listening')
        return
      }

      try {
        updateStatus('transcribing')
        const transcription = await transcribeAudio(blob)
        const text = transcription.text.trim()

        if (!text) {
          updateStatus('listening')
          return
        }

        setTranscript(text)
        const sessionId = ensureSession()
        onUserMessage(sessionId, text)

        updateStatus('thinking')
        const model = useModelStore.getState().selectedModel || undefined
        const response = await sendChatMessage({
          message: text,
          session_id: sessionId,
          model,
          response_mode: 'voice',
        })
        onAssistantMessage(sessionId, response)

        await playAudio(response)

        if (!cancelledRef.current && statusRef.current !== 'inactive') {
          updateStatus('listening')
        }
      } catch (e) {
        const message = e instanceof Error ? e.message : i18n.t('voiceSessionFailed')
        setError({ message })
        updateStatus('error')
      }
    },
    [ensureSession, onAssistantMessage, onUserMessage, playAudio, updateStatus],
  )

  const stopRecording = useCallback(() => {
    const recorder = recorderRef.current
    if (!recorder || recorder.state === 'inactive') {
      return
    }

    updateStatus('transcribing')
    recorder.stop()
  }, [updateStatus])

  const startRecording = useCallback(() => {
    const stream = streamRef.current
    if (!stream || statusRef.current !== 'listening') {
      return
    }

    const mimeType = pickMimeType()
    const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined)
    chunksRef.current = []
    silenceStartedAtRef.current = null
    recorderRef.current = recorder

    recorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        chunksRef.current.push(event.data)
      }
    }

    recorder.onstop = () => {
      const blob = new Blob(chunksRef.current, {
        type: recorder.mimeType || 'audio/webm',
      })
      chunksRef.current = []
      void processUtterance(blob)
    }

    recorder.start()
    updateStatus('recording')
  }, [processUtterance, updateStatus])

  const monitor = useCallback(() => {
    const analyser = analyserRef.current
    const data = dataRef.current
    if (!analyser || !data || statusRef.current === 'inactive') {
      return
    }

    const volume = getVolume(analyser, data)
    const now = performance.now()

    if (statusRef.current === 'listening' && volume > VOICE_THRESHOLD) {
      startRecording()
    }

    if (statusRef.current === 'recording') {
      if (volume < SILENCE_THRESHOLD) {
        silenceStartedAtRef.current ??= now
        if (now - silenceStartedAtRef.current > SILENCE_MS) {
          stopRecording()
        }
      } else {
        silenceStartedAtRef.current = null
      }
    }

    animationFrameRef.current = requestAnimationFrame(monitor)
  }, [startRecording, stopRecording])

  const start = useCallback(async () => {
    if (statusRef.current !== 'inactive') {
      return
    }

    try {
      cancelledRef.current = false
      setTranscript('')
      setError(null)
      updateStatus('entering')

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const audioContext = new AudioContext()
      const source = audioContext.createMediaStreamSource(stream)
      const analyser = audioContext.createAnalyser()
      analyser.fftSize = 2048
      source.connect(analyser)

      streamRef.current = stream
      audioContextRef.current = audioContext
      analyserRef.current = analyser
      dataRef.current = new Uint8Array(analyser.fftSize)

      updateStatus('listening')
      monitor()
    } catch (e) {
      const message = e instanceof Error ? e.message : i18n.t('voiceMicFailed')
      setError({ message })
      cleanupAudio()
      updateStatus('error')
    }
  }, [cleanupAudio, monitor, updateStatus])

  const interrupt = useCallback(() => {
    cleanupPlayer()
    if (statusRef.current !== 'inactive') {
      updateStatus('listening')
    }
  }, [cleanupPlayer, updateStatus])

  const exit = useCallback(() => {
    cancelledRef.current = true
    cleanupPlayer()
    cleanupAudio()
    setTranscript('')
    setError(null)
    updateStatus('inactive')
  }, [cleanupAudio, cleanupPlayer, updateStatus])

  return {
    status,
    transcript,
    error,
    isActive: status !== 'inactive',
    analyserRef,
    start,
    interrupt,
    exit,
  }
}
