import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  Legend, ResponsiveContainer, ReferenceLine, Dot
} from 'recharts'
import type { IterationRecord } from '../types'

interface Props {
  history: IterationRecord[]
}

const verdictColor = (verdict: string) => {
  if (verdict === 'GENUINE_IMPROVEMENT') return '#14b8a6'
  if (verdict === 'REWARD_HACKING') return '#ef4444'
  if (verdict === 'HARD_BLOCK') return '#f97316'
  return '#94a3b8'
}

function CustomDot(props: any) {
  const { cx, cy, payload } = props
  if (!payload) return null
  const color = verdictColor(payload.verdict)
  return (
    <g>
      <circle cx={cx} cy={cy} r={6} fill={color} stroke="white" strokeWidth={2} />
      {payload.verdict === 'REWARD_HACKING' && (
        <text x={cx} y={cy - 12} textAnchor="middle" fontSize={10} fill="#ef4444" fontWeight="bold">⚠</text>
      )}
      {payload.verdict === 'GENUINE_IMPROVEMENT' && (
        <text x={cx} y={cy - 12} textAnchor="middle" fontSize={10} fill="#14b8a6">✓</text>
      )}
    </g>
  )
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null
  const data = payload[0]?.payload
  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-lg p-3 text-xs">
      <p className="font-semibold text-gray-700 mb-1.5">Iteration {label} — <span className="font-mono text-teal-600">{data?.rule_version}</span></p>
      <p className="text-teal-600">Train: {((data?.train_score ?? 0) * 100).toFixed(0)}%</p>
      <p className="text-blue-500">Holdout: {((data?.holdout_score ?? 0) * 100).toFixed(0)}%</p>
      <p className={`mt-1 font-medium ${verdictColor(data?.verdict) === '#ef4444' ? 'text-red-500' : verdictColor(data?.verdict) === '#14b8a6' ? 'text-teal-600' : 'text-gray-400'}`}>
        {data?.verdict} → {data?.action}
      </p>
    </div>
  )
}

export function AccuracyChart({ history }: Props) {
  const data = history.map(h => ({
    iteration: h.iteration,
    train_score: h.train_score,
    holdout_score: h.holdout_score,
    verdict: h.verdict,
    rule_version: h.rule_version,
    action: h.action,
  }))

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
      <div className="px-5 py-4 border-b border-gray-100">
        <h2 className="text-sm font-semibold text-gray-800">Accuracy Over Iterations</h2>
        <p className="text-xs text-gray-400 mt-0.5">
          Genuine improvements accumulate · Reward hacking blocked
        </p>
      </div>

      <div className="p-5">
        {history.length === 0 ? (
          <div className="flex items-center justify-center h-40 text-sm text-gray-400">
            No iterations yet. Complete verify + approve/reject to see chart.
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={data} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey="iteration" tick={{ fontSize: 11, fill: '#94a3b8' }} tickLine={false} />
              <YAxis domain={[0, 1]} tickFormatter={v => `${(v * 100).toFixed(0)}%`}
                tick={{ fontSize: 11, fill: '#94a3b8' }} tickLine={false} axisLine={false} />
              <Tooltip content={<CustomTooltip />} />
              <Legend iconType="circle" iconSize={8}
                formatter={(v) => <span className="text-xs text-gray-500">{v === 'train_score' ? 'Train' : 'Holdout'}</span>} />
              <ReferenceLine y={1} stroke="#e2e8f0" strokeDasharray="4 4" />
              <Line type="monotone" dataKey="train_score" stroke="#14b8a6" strokeWidth={2}
                dot={<CustomDot />} activeDot={{ r: 7 }} name="train_score" />
              <Line type="monotone" dataKey="holdout_score" stroke="#3b82f6" strokeWidth={2}
                dot={<CustomDot />} activeDot={{ r: 7 }} strokeDasharray="5 3" name="holdout_score" />
            </LineChart>
          </ResponsiveContainer>
        )}

        {history.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-2">
            {history.map(h => (
              <div key={h.iteration} className={`text-xs px-2.5 py-1 rounded-full border font-medium ${
                h.verdict === 'GENUINE_IMPROVEMENT' ? 'bg-teal-50 text-teal-700 border-teal-200' :
                h.verdict === 'REWARD_HACKING' ? 'bg-red-50 text-red-600 border-red-200' :
                h.verdict === 'HARD_BLOCK' ? 'bg-orange-50 text-orange-700 border-orange-200' :
                'bg-gray-50 text-gray-500 border-gray-200'
              }`}>
                #{h.iteration} {h.rule_version} → {h.action}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
