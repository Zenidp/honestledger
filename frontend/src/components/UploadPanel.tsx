import { useState, useRef } from 'react'
import { uploadData } from '../api'
import { Upload, FileText, CheckCircle, X } from 'lucide-react'

interface Props {
  onUploaded: () => void
}

export default function UploadPanel({ onUploaded }: Props) {
  const [paymentsFile, setPaymentsFile] = useState<File | null>(null)
  const [invoicesFile, setInvoicesFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<{ payments: number; invoices: number } | null>(null)
  const [error, setError] = useState<string | null>(null)
  const paymentsRef = useRef<HTMLInputElement>(null)
  const invoicesRef = useRef<HTMLInputElement>(null)

  const handleUpload = async () => {
    if (!paymentsFile || !invoicesFile) return
    setLoading(true)
    setError(null)
    try {
      const res = await uploadData(paymentsFile, invoicesFile)
      setResult({ payments: res.payments, invoices: res.invoices })
      onUploaded()
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? e?.message ?? 'Upload failed')
    } finally {
      setLoading(false)
    }
  }

  const FileSlot = ({
    label, file, onFile, inputRef
  }: { label: string; file: File | null; onFile: (f: File) => void; inputRef: React.RefObject<HTMLInputElement> }) => (
    <div
      onClick={() => inputRef.current?.click()}
      className="border-2 border-dashed border-gray-200 rounded-xl p-4 cursor-pointer hover:border-teal-400 hover:bg-teal-50/30 transition-colors"
    >
      <input
        ref={inputRef}
        type="file"
        accept=".csv"
        className="hidden"
        onChange={e => e.target.files?.[0] && onFile(e.target.files[0])}
      />
      <div className="flex items-center gap-3">
        {file ? (
          <CheckCircle className="w-5 h-5 text-teal-500 shrink-0" />
        ) : (
          <FileText className="w-5 h-5 text-gray-400 shrink-0" />
        )}
        <div className="min-w-0">
          <p className="text-sm font-medium text-gray-700">{label}</p>
          <p className="text-xs text-gray-400 truncate">{file ? file.name : 'Click to select CSV'}</p>
        </div>
      </div>
    </div>
  )

  return (
    <div className="bg-white rounded-2xl border border-gray-100 p-5 space-y-4">
      <div className="flex items-center gap-2">
        <Upload className="w-4 h-4 text-teal-600" />
        <h3 className="font-semibold text-gray-800 text-sm">Upload Your Data</h3>
      </div>

      <div className="space-y-2">
        <FileSlot label="payments.csv" file={paymentsFile} onFile={setPaymentsFile} inputRef={paymentsRef} />
        <FileSlot label="invoices.csv" file={invoicesFile} onFile={setInvoicesFile} inputRef={invoicesRef} />
      </div>

      {error && <p className="text-xs text-red-600 bg-red-50 rounded-lg px-3 py-2">{error}</p>}

      {result && (
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
  )
}
