import { motion, AnimatePresence } from 'framer-motion'
import { AlertTriangle, X, ShieldAlert } from 'lucide-react'

interface Props {
  visible: boolean
  explanation?: string
  onDismiss?: () => void
}

export function RewardHackBanner({ visible, explanation, onDismiss }: Props) {
  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          initial={{ opacity: 0, y: -20, scale: 0.98 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: -20, scale: 0.98 }}
          transition={{ type: 'spring', stiffness: 300, damping: 25 }}
          className="fixed top-4 left-1/2 -translate-x-1/2 z-50 w-full max-w-2xl px-4"
        >
          <motion.div
            animate={{ boxShadow: ['0 0 0 0 rgba(239,68,68,0.4)', '0 0 0 12px rgba(239,68,68,0)', '0 0 0 0 rgba(239,68,68,0)'] }}
            transition={{ repeat: 3, duration: 1.2 }}
            className="bg-red-600 text-white rounded-xl shadow-2xl overflow-hidden border border-red-500"
          >
            {/* Animated stripe background */}
            <div className="absolute inset-0 opacity-10"
              style={{
                backgroundImage: 'repeating-linear-gradient(-45deg, transparent, transparent 8px, rgba(255,255,255,0.3) 8px, rgba(255,255,255,0.3) 16px)',
              }} />

            <div className="relative p-5">
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-start gap-3">
                  <motion.div
                    animate={{ rotate: [0, -10, 10, -10, 10, 0] }}
                    transition={{ delay: 0.3, duration: 0.6 }}>
                    <ShieldAlert className="w-6 h-6 text-red-200 flex-shrink-0 mt-0.5" />
                  </motion.div>
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <AlertTriangle className="w-4 h-4 text-red-200" />
                      <span className="text-xs font-bold tracking-widest uppercase text-red-200">
                        HonestLedger Alert
                      </span>
                    </div>
                    <h3 className="text-lg font-bold leading-tight">
                      Reward Hacking Detected
                    </h3>
                    <p className="text-red-100 text-sm mt-1 leading-relaxed">
                      Rule proposal auto-rejected. This agent caught itself cheating.
                    </p>
                    {explanation && (
                      <p className="text-red-200 text-xs mt-2 font-mono leading-relaxed border-t border-red-500 pt-2">
                        {explanation}
                      </p>
                    )}
                  </div>
                </div>
                {onDismiss && (
                  <button onClick={onDismiss}
                    className="p-1.5 rounded-lg hover:bg-red-500 transition-colors flex-shrink-0">
                    <X className="w-4 h-4 text-red-200" />
                  </button>
                )}
              </div>
            </div>

            {/* Pulse bar at bottom */}
            <motion.div className="h-1 bg-red-400"
              animate={{ scaleX: [0, 1] }}
              transition={{ duration: 0.8, ease: 'easeOut' }}
              style={{ transformOrigin: 'left' }} />
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
