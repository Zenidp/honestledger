import { useState } from 'react'
import { setApiKey } from '../api'
import { KeyRound, ShieldCheck } from 'lucide-react'

interface Props {
  onAuthenticated: () => void
}

export default function ApiKeyGate({ onAuthenticated }: Props) {
  const [key, setKey] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!key.startsWith('hl_')) {
      setError('API key must start with hl_')
      return
    }
    setLoading(true)
    setError(null)
    try {
      setApiKey(key.trim())
      // Validate by calling /status
      const res = await fetch('/api/status', { headers: { 'X-API-Key': key.trim() } })
      if (res.status === 401) {
        setError('Invalid or inactive API key.')
        localStorage.removeItem('hl_api_key')
      } else {
        onAuthenticated()
      }
    } catch {
      setError('Connection error. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-lg p-8 w-full max-w-md">
        <div className="flex items-center gap-3 mb-6">
          <div className="p-2 bg-teal-50 rounded-xl">
            <ShieldCheck className="w-6 h-6 text-teal-600" />
          </div>
          <div>
            <h1 className="text-xl font-semibold text-gray-900">HonestLedger</h1>
            <p className="text-sm text-gray-500">Enter your API key to continue</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              API Key
            </label>
            <div className="relative">
              <KeyRound className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="password"
                value={key}
                onChange={e => setKey(e.target.value)}
                placeholder="hl_••••••••••••••••••••••••••••••••"
                className="w-full pl-10 pr-4 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 font-mono"
                autoFocus
              />
            </div>
          </div>

          {error && (
            <p className="text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2">{error}</p>
          )}

          <button
            type="submit"
            disabled={!key || loading}
            className="w-full py-2.5 bg-teal-600 hover:bg-teal-700 disabled:bg-gray-200 disabled:text-gray-400 text-white font-medium rounded-lg text-sm transition-colors"
          >
            {loading ? 'Validating…' : 'Access Dashboard'}
          </button>
        </form>

        <p className="text-xs text-gray-400 mt-4 text-center">
          API keys are stored locally and never sent to third parties.
        </p>
      </div>
    </div>
  )
}
