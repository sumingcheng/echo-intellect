import { useEffect, useRef } from 'react'
import type { VoiceSessionStatus } from './voiceTypes'

type RGB = [number, number, number]

interface SpringVal { cur: number; vel: number }

interface StateStyle {
  core: RGB
  glow: RGB
  bar: RGB
  intensity: number
}

const PALETTE: Record<VoiceSessionStatus, StateStyle> = {
  inactive:     { core: [30,  30,  38],  glow: [50,  50,  70],  bar: [60,  60,  80],  intensity: 0.0  },
  entering:     { core: [55,  48,  95],  glow: [110, 90,  195], bar: [130, 110, 220], intensity: 0.15 },
  listening:    { core: [75,  65,  160], glow: [120, 110, 250], bar: [150, 140, 255], intensity: 0.35 },
  recording:    { core: [220, 140, 50],  glow: [255, 180, 65],  bar: [255, 200, 100], intensity: 0.7  },
  transcribing: { core: [65,  100, 195], glow: [95,  150, 255], bar: [120, 175, 255], intensity: 0.4  },
  thinking:     { core: [145, 70,  215], glow: [200, 110, 255], bar: [220, 150, 255], intensity: 0.45 },
  speaking:     { core: [45,  190, 140], glow: [65,  255, 205], bar: [100, 255, 220], intensity: 0.65 },
  error:        { core: [215, 55,  50],  glow: [255, 90,  75],  bar: [255, 120, 100], intensity: 0.5  },
}

const BAR_COUNT = 64
const SMOOTH_FACTOR = 0.25

function stepSpring(s: SpringVal, target: number, stiffness: number, damping: number, dt: number) {
  s.vel += (target - s.cur) * stiffness * dt
  s.vel *= Math.pow(damping, dt * 60)
  s.cur += s.vel * dt
}

function lerpRGB(cur: RGB, vel: RGB, target: RGB, stiffness: number, damping: number, dt: number) {
  for (let i = 0; i < 3; i++) {
    vel[i] += (target[i] - cur[i]) * stiffness * dt
    vel[i] *= Math.pow(damping, dt * 60)
    cur[i] += vel[i] * dt
  }
}

interface AudioOrbProps {
  status: VoiceSessionStatus
  analyserRef: React.RefObject<AnalyserNode | null>
  size?: number
}

export default function AudioOrb({ status, analyserRef, size = 380 }: AudioOrbProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const frameRef = useRef(0)
  const statusRef = useRef(status)
  statusRef.current = status

  const st = useRef({
    coreC: [...PALETTE.inactive.core] as RGB,
    coreV: [0, 0, 0] as RGB,
    glowC: [...PALETTE.inactive.glow] as RGB,
    glowV: [0, 0, 0] as RGB,
    barC: [...PALETTE.inactive.bar] as RGB,
    barV: [0, 0, 0] as RGB,
    intensity: { cur: 0, vel: 0 } as SpringVal,
    scale: { cur: 0.5, vel: 0 } as SpringVal,
    bars: new Float32Array(BAR_COUNT),
    barTargets: new Float32Array(BAR_COUNT),
    freqBuf: null as Uint8Array | null,
    lastT: 0,
    rotation: 0,
  })

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) { return }
    const ctx = canvas.getContext('2d')
    if (!ctx) { return }

    const dpr = window.devicePixelRatio || 1
    canvas.width = size * dpr
    canvas.height = size * dpr
    ctx.scale(dpr, dpr)

    const cx = size / 2
    const cy = size / 2
    const coreR = size * 0.18
    const s = st.current
    s.lastT = performance.now() / 1000

    const tick = () => {
      const now = performance.now() / 1000
      const dt = Math.min(now - s.lastT, 0.05)
      s.lastT = now
      const t = now

      const curStatus = statusRef.current
      const target = PALETTE[curStatus]

      // 音频数据
      const analyser = analyserRef.current
      const hasAudio = curStatus === 'recording' || curStatus === 'speaking'

      if (analyser) {
        if (!s.freqBuf) {
          s.freqBuf = new Uint8Array(analyser.frequencyBinCount)
        }
        analyser.getByteFrequencyData(s.freqBuf)

        const binCount = s.freqBuf.length
        const binsPerBar = Math.max(1, Math.floor(binCount / BAR_COUNT))

        for (let i = 0; i < BAR_COUNT; i++) {
          let sum = 0
          const start = i * binsPerBar
          for (let j = start; j < start + binsPerBar && j < binCount; j++) {
            sum += s.freqBuf[j] / 255
          }
          s.barTargets[i] = sum / binsPerBar
        }
      }

      // 无音频数据时的模拟
      if (!analyser || !hasAudio) {
        for (let i = 0; i < BAR_COUNT; i++) {
          const angle = (i / BAR_COUNT) * Math.PI * 2
          if (curStatus === 'speaking') {
            s.barTargets[i] = 0.12 + Math.sin(t * 3.5 + angle * 3) * 0.08
              + Math.sin(t * 5.8 + angle * 5) * 0.04
              + Math.sin(t * 8.1 + angle * 7) * 0.02
          } else if (curStatus === 'thinking' || curStatus === 'transcribing') {
            s.barTargets[i] = 0.03 + Math.sin(t * 1.5 + angle * 2) * 0.02
          } else if (curStatus === 'listening') {
            s.barTargets[i] = 0.015 + Math.sin(t * 0.8 + angle * 3) * 0.01
          } else {
            s.barTargets[i] = 0
          }
        }
      }

      // 频谱平滑
      for (let i = 0; i < BAR_COUNT; i++) {
        s.bars[i] += (s.barTargets[i] - s.bars[i]) * SMOOTH_FACTOR
      }

      // 弹簧
      lerpRGB(s.coreC, s.coreV, target.core, 3.5, 0.82, dt)
      lerpRGB(s.glowC, s.glowV, target.glow, 3.5, 0.82, dt)
      lerpRGB(s.barC, s.barV, target.bar, 4, 0.80, dt)
      stepSpring(s.intensity, target.intensity, 4, 0.84, dt)

      const targetScale = curStatus === 'inactive' ? 0.5
        : curStatus === 'entering' ? 0.85
        : 1.0
      stepSpring(s.scale, targetScale, 5, 0.76, dt)

      const sc = s.scale.cur
      const inten = s.intensity.cur
      const [cr, cg, cb] = s.coreC
      const [gr, gg, gb] = s.glowC
      const [br, bg, bb] = s.barC

      // 呼吸
      const breathAmp = curStatus === 'recording' ? 0.025 : curStatus === 'speaking' ? 0.02 : 0.012
      const breathSpd = curStatus === 'thinking' ? 0.6 : 0.9
      const breath = 1 + Math.sin(t * breathSpd * Math.PI * 2) * breathAmp

      const effectiveR = coreR * sc * breath

      // 旋转（thinking/transcribing 快速，其他缓慢）
      const rotSpeed = (curStatus === 'thinking' || curStatus === 'transcribing') ? 0.4 : 0.05
      s.rotation += rotSpeed * dt

      ctx.clearRect(0, 0, size, size)

      // Layer 1: 远景辉光
      const glowR1 = effectiveR * 3.2
      const g1 = ctx.createRadialGradient(cx, cy, effectiveR * 0.3, cx, cy, glowR1)
      g1.addColorStop(0, `rgba(${gr},${gg},${gb},${inten * 0.35})`)
      g1.addColorStop(0.35, `rgba(${gr},${gg},${gb},${inten * 0.08})`)
      g1.addColorStop(0.7, `rgba(${gr},${gg},${gb},${inten * 0.015})`)
      g1.addColorStop(1, 'rgba(0,0,0,0)')
      ctx.fillStyle = g1
      ctx.beginPath()
      ctx.arc(cx, cy, glowR1, 0, Math.PI * 2)
      ctx.fill()

      // Layer 2: 频谱线条
      const barMinLen = 2
      const barMaxLen = size * 0.16
      const barGap = effectiveR + 6
      const barWidth = Math.max(1.5, (Math.PI * 2 * barGap) / BAR_COUNT * 0.55)

      ctx.lineCap = 'round'
      for (let i = 0; i < BAR_COUNT; i++) {
        const angle = (i / BAR_COUNT) * Math.PI * 2 + s.rotation
        const val = s.bars[i]
        const len = barMinLen + val * barMaxLen * inten * 3

        if (len < 0.5) { continue }

        const x0 = cx + Math.cos(angle) * barGap
        const y0 = cy + Math.sin(angle) * barGap
        const x1 = cx + Math.cos(angle) * (barGap + len)
        const y1 = cy + Math.sin(angle) * (barGap + len)

        const alpha = 0.3 + val * 0.7
        ctx.strokeStyle = `rgba(${Math.round(br)},${Math.round(bg)},${Math.round(bb)},${alpha * inten})`
        ctx.lineWidth = barWidth
        ctx.beginPath()
        ctx.moveTo(x0, y0)
        ctx.lineTo(x1, y1)
        ctx.stroke()
      }

      // Layer 3: 核心圆 — 干净的正圆，不变形
      const coreGrad = ctx.createRadialGradient(
        cx - effectiveR * 0.25, cy - effectiveR * 0.25, 0,
        cx + effectiveR * 0.05, cy + effectiveR * 0.05, effectiveR,
      )
      coreGrad.addColorStop(0, `rgba(${Math.min(cr + 50, 255)},${Math.min(cg + 40, 255)},${Math.min(cb + 40, 255)},0.97)`)
      coreGrad.addColorStop(0.65, `rgba(${cr},${cg},${cb},1)`)
      coreGrad.addColorStop(1, `rgba(${Math.max(cr - 15, 0)},${Math.max(cg - 15, 0)},${Math.max(cb - 15, 0)},1)`)
      ctx.fillStyle = coreGrad
      ctx.beginPath()
      ctx.arc(cx, cy, effectiveR, 0, Math.PI * 2)
      ctx.fill()

      // Layer 4: 核心高光
      const hlGrad = ctx.createRadialGradient(
        cx - effectiveR * 0.3, cy - effectiveR * 0.35, 0,
        cx, cy, effectiveR * 0.6,
      )
      hlGrad.addColorStop(0, 'rgba(255,255,255,0.18)')
      hlGrad.addColorStop(0.35, 'rgba(255,255,255,0.06)')
      hlGrad.addColorStop(1, 'rgba(255,255,255,0)')
      ctx.fillStyle = hlGrad
      ctx.beginPath()
      ctx.arc(cx, cy, effectiveR, 0, Math.PI * 2)
      ctx.fill()

      // Layer 5: 核心边缘光
      if (inten > 0.05) {
        ctx.strokeStyle = `rgba(${Math.round(gr)},${Math.round(gg)},${Math.round(gb)},${inten * 0.3})`
        ctx.lineWidth = 1.5
        ctx.beginPath()
        ctx.arc(cx, cy, effectiveR + 1, 0, Math.PI * 2)
        ctx.stroke()
      }

      // Layer 6: 脉冲波纹（recording / speaking）
      if (curStatus === 'recording' || curStatus === 'speaking') {
        for (let ri = 0; ri < 3; ri++) {
          const phase = ((t * 0.6 + ri * 0.33) % 1)
          const ringR = effectiveR + 8 + phase * size * 0.18
          const alpha = (1 - phase) * (1 - phase) * inten * 0.25
          if (alpha > 0.003) {
            ctx.strokeStyle = `rgba(${Math.round(gr)},${Math.round(gg)},${Math.round(gb)},${alpha})`
            ctx.lineWidth = 1.2 * (1 - phase)
            ctx.beginPath()
            ctx.arc(cx, cy, ringR, 0, Math.PI * 2)
            ctx.stroke()
          }
        }
      }

      // Layer 7: 旋转弧（thinking / transcribing）
      if (curStatus === 'thinking' || curStatus === 'transcribing') {
        const arcR = effectiveR + 10
        const arcAngle = t * 2.0
        ctx.lineCap = 'round'
        ctx.lineWidth = 2.5
        ctx.strokeStyle = `rgba(${Math.round(gr)},${Math.round(gg)},${Math.round(gb)},${inten * 0.6})`
        ctx.beginPath()
        ctx.arc(cx, cy, arcR, arcAngle, arcAngle + Math.PI * 0.5)
        ctx.stroke()
        ctx.strokeStyle = `rgba(${Math.round(gr)},${Math.round(gg)},${Math.round(gb)},${inten * 0.3})`
        ctx.beginPath()
        ctx.arc(cx, cy, arcR, arcAngle + Math.PI, arcAngle + Math.PI + Math.PI * 0.3)
        ctx.stroke()
      }

      frameRef.current = requestAnimationFrame(tick)
    }

    frameRef.current = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frameRef.current)
  }, [size, analyserRef])

  return (
    <canvas
      ref={canvasRef}
      style={{ width: size, height: size }}
      className="pointer-events-none"
    />
  )
}
