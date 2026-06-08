import { useState, useEffect } from 'react'
import { Clock } from 'lucide-react'

interface Props {
  running: boolean
}

export function ElapsedTimer({ running }: Props) {
  const [seconds, setSeconds] = useState(0)

  useEffect(() => {
    if (!running) { setSeconds(0); return }
    const id = setInterval(() => setSeconds(s => s + 1), 1000)
    return () => clearInterval(id)
  }, [running])

  if (!running && seconds === 0) return null

  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  const label = m > 0 ? `${m}m ${s}s` : `${s}s`

  return (
    <div className="flex items-center gap-1 text-xs text-gray-400 tabular-nums">
      <Clock className="w-3 h-3" />
      <span>{label}</span>
    </div>
  )
}
