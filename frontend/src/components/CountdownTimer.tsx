import { useState, useEffect } from 'react'
import { Clock } from 'lucide-react'

interface Props {
  seconds: number
}

export function CountdownTimer({ seconds }: Props) {
  const [remaining, setRemaining] = useState(seconds)

  useEffect(() => {
    setRemaining(seconds)
    const interval = setInterval(() => {
      setRemaining(prev => (prev <= 1 ? 0 : prev - 1))
    }, 1000)
    return () => clearInterval(interval)
  }, [seconds])

  if (remaining === 0) {
    return (
      <span className="text-xs text-gray-400 flex items-center gap-1">
        <Clock className="w-3 h-3" />
        Almost there...
      </span>
    )
  }

  return (
    <span className="text-xs text-gray-400 flex items-center gap-1 tabular-nums">
      <Clock className="w-3 h-3" />
      ~{remaining}s remaining
    </span>
  )
}
