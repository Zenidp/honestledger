import { useState, useRef } from 'react'
import { uploadData } from '../api'
import { Upload, FileText, CheckCircle, AlertTriangle, Info, X, BookOpen, ChevronDown, ChevronUp } from 'lucide-react'

// ── Format guide data ──────────────────────────────────────────────────────────

const FORMAT_GUIDE = {
  payments: {
    label: 'Payments CSV',
    color: 'teal',
    fields: [
      { name: 'id', required: true,  aliases: ['id', 'no_transaksi', 'payment_id', 'transaction_id', 'trx_id'] },
      { name: 'payer_name', required: true,  aliases: ['payer_name', 'nama_pengirim', 'payer', 'sender', 'customer', 'pembayar'] },
      { name: 'amount', required: true,  aliases: ['amount', 'nominal', 'jumlah', 'total', 'value', 'debit'] },
      { name: 'date', required: false, aliases: ['date', 'tanggal', 'payment_date', 'transaction_date', 'tgl'] },
      { name: 'reference', required: false, aliases: ['reference', 'keterangan', 'description', 'memo', 'note', 'remarks'] },
    ],
  },
  invoices: {
    label: 'Invoices CSV',
    color: 'indigo',
    fields: [
      { name: 'id', required: true,  aliases: ['id', 'no_invoice', 'invoice_id', 'invoice_number', 'inv_id'] },
      { name: 'vendor_name', required: true,  aliases: ['vendor_name', 'nama_vendor', 'vendor', 'supplier', 'company_name', 'nama_perusahaan'] },
      { name: 'amount', required: true,  aliases: ['amount', 'total_tagihan', 'nominal', 'jumlah', 'invoice_amount'] },
      { name: 'date', required: false, aliases: ['date', 'tanggal_invoice', 'invoice_date', 'tgl_invoice', 'tgl'] },
      { name: 'invoice_number', required: false, aliases: ['invoice_number', 'no_invoice', 'inv_no', 'inv_number'] },
    ],
  },
}

// ── Format Guide Modal ─────────────────────────────────────────────────────────

function FormatGuideModal({ onClose }: { onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div
        className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-gray-100 sticky top-0 bg-white rounded-t-2xl z-10">
          <div className="flex items-center gap-2">
            <BookOpen className="w-5 h-5 text-teal-600" />
            <h2 className="text-base font-semibold text-gray-900">CSV Format Guide</h2>
          </div>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded-lg transition-colors">
            <X className="w-4 h-4 text-gray-500" />
          </button>
        </div>

        <div className="p-5 space-y-5">
          <p className="text-sm text-gray-500">
            HonestLedger auto-detects column names. The table below shows all accepted names for each field.
            <strong className="text-gray-700"> Required fields must be present</strong> — optional fields improve matching quality.
          </p>

          {(['payments', 'invoices'] as const).map(type => {
            const guide = FORMAT_GUIDE[type]
            const borderColor = type === 'payments' ? 'border-teal-200' : 'border-indigo-200'
            const headerBg   = type === 'payments' ? 'bg-teal-600'    : 'bg-indigo-600'
            return (
              <div key={type} className={`border ${borderColor} rounded-xl overflow-hidden`}>
                <div className={`${headerBg} px-4 py-2.5`}>
                  <h3 className="text-sm font-semibold text-white">{guide.label}</h3>
                </div>
                <table className="w-full text-xs">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="text-left px-4 py-2 font-medium text-gray-600 w-28">Field</th>
                      <th className="text-left px-4 py-2 font-medium text-gray-600 w-20">Required</th>
                      <th className="text-left px-4 py-2 font-medium text-gray-600">Accepted column names</th>
                    </tr>
                  </thead>
                  <tbody>
                    {guide.fields.map((f, i) => (
                      <tr key={f.name} className={i % 2 === 0 ? 'bg-white' : 'bg-gray-50/50'}>
                        <td className="px-4 py-2 font-mono text-gray-800 font-medium">{f.name}</td>
                        <td className="px-4 py-2">
                          {f.required ? (
                            <span className="text-xs bg-red-100 text-red-700 px-1.5 py-0.5 rounded font-medium">Required</span>
                          ) : (
                            <span className="text-xs bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded">Optional</span>
                          )}
                        </td>
                        <td className="px-4 py-2">
                          <div className="flex flex-wrap gap-1">
                            {f.aliases.map(a => (
                              <code key={a} className="bg-gray-100 text-gray-700 px-1.5 py-0.5 rounded text-xs">{a}</code>
                            ))}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )
          })}

          {/* Example snippet */}
          <div className="bg-gray-900 rounded-xl p-4">
            <p className="text-xs text-gray-400 mb-2 font-medium">Example payments.csv</p>
            <pre className="text-xs text-green-400 font-mono whitespace-pre">{`id,date,payer_name,amount,reference
TRX-001,2024-01-05,PT Mitra Solusi,15000000,Invoice Jan 2024
TRX-002,2024-01-08,Teknologi Maju,8500000,Proyek Alpha`}</pre>
          </div>

          <p className="text-xs text-gray-400">
            Tip: If your column name is not in the list, rename it before uploading.
            The system will warn you if any important column is missing.
          </p>
        </div>
      </div>
    </div>
  )
}

// ── File Slot ──────────────────────────────────────────────────────────────────

interface FileSlotProps {
  label: string
  sublabel?: string
  file: File | null
  onFile: (f: File) => void
  inputRef: React.RefObject<HTMLInputElement>
}

function FileSlot({ label, sublabel, file, onFile, inputRef }: FileSlotProps) {
  return (
    <div
      onClick={() => inputRef.current?.click()}
      className="border-2 border-dashed border-gray-200 rounded-xl p-4 cursor-pointer hover:border-teal-400 hover:bg-teal-50/30 transition-colors"
    >
      <input ref={inputRef} type="file" accept=".csv" className="hidden"
        onChange={e => e.target.files?.[0] && onFile(e.target.files[0])} />
      <div className="flex items-center gap-3">
        {file
          ? <CheckCircle className="w-5 h-5 text-teal-500 shrink-0" />
          : <FileText className="w-5 h-5 text-gray-400 shrink-0" />
        }
        <div className="min-w-0">
          <p className="text-sm font-medium text-gray-700">{label}</p>
          <p className="text-xs text-gray-400 truncate">{file ? file.name : sublabel ?? 'Click to select CSV'}</p>
        </div>
      </div>
    </div>
  )
}

// ── Column Warning Item ────────────────────────────────────────────────────────

function ColumnWarning({ warn }: { warn: { missing_field: string; critical: boolean; suggested_names: string[]; file: string } }) {
  const [open, setOpen] = useState(false)
  return (
    <div className={`rounded-lg border text-xs ${warn.critical ? 'bg-red-50 border-red-200' : 'bg-amber-50 border-amber-200'}`}>
      <button
        onClick={() => setOpen(o => !o)}
        className="flex items-center justify-between w-full px-3 py-2 text-left"
      >
        <div className="flex items-center gap-2">
          <AlertTriangle className={`w-3.5 h-3.5 shrink-0 ${warn.critical ? 'text-red-500' : 'text-amber-500'}`} />
          <span className={`font-medium ${warn.critical ? 'text-red-700' : 'text-amber-700'}`}>
            {warn.critical ? 'Required' : 'Optional'} column <code className="font-mono bg-white/60 px-1 rounded">{warn.missing_field}</code> not found in <em>{warn.file}</em>
          </span>
        </div>
        {open ? <ChevronUp className="w-3 h-3 text-gray-400 shrink-0" /> : <ChevronDown className="w-3 h-3 text-gray-400 shrink-0" />}
      </button>
      {open && (
        <div className="px-3 pb-2 text-gray-600">
          Rename one of your columns to:{' '}
          {warn.suggested_names.map(n => (
            <code key={n} className="bg-white/80 border border-gray-200 px-1 rounded mr-1">{n}</code>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Main Component ─────────────────────────────────────────────────────────────

interface ColumnWarn {
  file: string
  file_type: string
  missing_field: string
  critical: boolean
  suggested_names: string[]
  message: string
}

interface Props {
  onUploaded: () => void
}

export default function UploadPanel({ onUploaded }: Props) {
  const [paymentsFile, setPaymentsFile] = useState<File | null>(null)
  const [invoicesFile, setInvoicesFile] = useState<File | null>(null)
  const [loading, setLoading]     = useState(false)
  const [result,  setResult]      = useState<{ payments: number; invoices: number } | null>(null)
  const [error,   setError]       = useState<string | null>(null)
  const [colWarns, setColWarns]   = useState<ColumnWarn[]>([])
  const [showGuide, setShowGuide] = useState(false)
  const paymentsRef = useRef<HTMLInputElement>(null)
  const invoicesRef = useRef<HTMLInputElement>(null)

  const handleUpload = async () => {
    if (!paymentsFile || !invoicesFile) return
    setLoading(true)
    setError(null)
    setColWarns([])
    try {
      const res = await uploadData(paymentsFile, invoicesFile)
      setColWarns(res.column_warnings ?? [])
      setResult({ payments: res.payments, invoices: res.invoices })
      if (!(res.column_warnings ?? []).some((w: ColumnWarn) => w.critical)) {
        onUploaded()
      }
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? e?.message ?? 'Upload failed')
    } finally {
      setLoading(false)
    }
  }

  const hasCritical = colWarns.some(w => w.critical)

  return (
    <>
      <div className="bg-white rounded-2xl border border-gray-100 p-5 space-y-4">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Upload className="w-4 h-4 text-teal-600" />
            <h3 className="font-semibold text-gray-800 text-sm">Upload Your Data</h3>
          </div>
          <button
            onClick={() => setShowGuide(true)}
            className="flex items-center gap-1 text-xs text-teal-600 hover:text-teal-800 transition-colors"
          >
            <Info className="w-3.5 h-3.5" />
            Format Guide
          </button>
        </div>

        {/* File slots */}
        <div className="space-y-2">
          <FileSlot label="payments.csv" sublabel="Bank mutation / payment report"
            file={paymentsFile} onFile={setPaymentsFile} inputRef={paymentsRef} />
          <FileSlot label="invoices.csv" sublabel="Vendor invoice list"
            file={invoicesFile} onFile={setInvoicesFile} inputRef={invoicesRef} />
        </div>

        {/* Error */}
        {error && <p className="text-xs text-red-600 bg-red-50 rounded-lg px-3 py-2">{error}</p>}

        {/* Column warnings */}
        {colWarns.length > 0 && (
          <div className="space-y-1.5">
            <p className="text-xs font-medium text-gray-600 flex items-center gap-1">
              <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
              {colWarns.length} column issue{colWarns.length > 1 ? 's' : ''} detected — fix to improve results
            </p>
            {colWarns.map((w, i) => <ColumnWarning key={i} warn={w} />)}
            {hasCritical && (
              <p className="text-xs text-red-600 bg-red-50 rounded-lg px-3 py-1.5">
                Required columns are missing. Reconciliation will not work correctly until fixed.
              </p>
            )}
            {!hasCritical && (
              <button
                onClick={onUploaded}
                className="w-full py-1.5 border border-teal-400 text-teal-700 text-xs font-medium rounded-lg hover:bg-teal-50 transition-colors"
              >
                Continue anyway (optional columns only)
              </button>
            )}
          </div>
        )}

        {/* Success */}
        {result && colWarns.length === 0 && (
          <p className="text-xs text-teal-700 bg-teal-50 rounded-lg px-3 py-2">
            ✓ Uploaded {result.payments} payments · {result.invoices} invoices
          </p>
        )}

        <button
          onClick={handleUpload}
          disabled={!paymentsFile || !invoicesFile || loading}
          className="w-full py-2 bg-teal-600 hover:bg-teal-700 disabled:bg-gray-100 disabled:text-gray-400 text-white text-sm font-medium rounded-lg transition-colors"
        >
          {loading ? 'Uploading…' : 'Upload & Process'}
        </button>
      </div>

      {showGuide && <FormatGuideModal onClose={() => setShowGuide(false)} />}
    </>
  )
}
