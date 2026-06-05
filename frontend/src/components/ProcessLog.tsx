import { motion, AnimatePresence } from 'framer-motion'

interface Props {
  steps: string[]
  running: boolean
}

export function ProcessLog({ steps, running }: Props) {
  if (steps.length === 0 && !running) return null

  return (
    <div className="mt-3 pt-3 border-t border-gray-100 space-y-1.5">
      <AnimatePresence initial={false}>
        {steps.map((step, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, y: 3 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.18 }}
            className="flex items-start gap-2 text-xs"
          >
            <span className="text-teal-400 shrink-0 mt-px select-none">▸</span>
            <span className={i === steps.length - 1 && running
              ? 'text-teal-600 font-medium'
              : i === steps.length - 1
              ? 'text-gray-700'
              : 'text-gray-400'
            }>
              {step}
            </span>
          </motion.div>
        ))}
      </AnimatePresence>

      {running && (
        <div className="flex items-center gap-1.5 text-xs text-gray-300 pl-4">
          <span className="w-1 h-1 bg-teal-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
          <span className="w-1 h-1 bg-teal-400 rounded-full animate-bounce" style={{ animationDelay: '160ms' }} />
          <span className="w-1 h-1 bg-teal-400 rounded-full animate-bounce" style={{ animationDelay: '320ms' }} />
        </div>
      )}
    </div>
  )
}
