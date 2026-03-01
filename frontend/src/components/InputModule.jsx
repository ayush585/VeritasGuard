function InputModule({
  mode,
  onModeChange,
  input,
  onInputChange,
  file,
  onFileChange,
  loading,
  inputError,
  onSubmit,
  sampleCases,
  onUseSample,
}) {
  return (
    <section className="panel input-module entering" aria-label="Verification Input Module">
      <div className="panel-head">
        <h2>Run Live Verification</h2>
        <p>Paste or upload suspicious content. VeritasGuard will orchestrate multilingual verification agents.</p>
      </div>

      <div className="mode-switch" role="tablist" aria-label="Input mode">
        <button
          type="button"
          role="tab"
          aria-selected={mode === 'text'}
          className={mode === 'text' ? 'active' : ''}
          onClick={() => onModeChange('text')}
          disabled={loading}
        >
          Text Claim
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={mode === 'image'}
          className={mode === 'image' ? 'active' : ''}
          onClick={() => onModeChange('image')}
          disabled={loading}
        >
          Image Proof
        </button>
      </div>

      <label className="field">
        <span>Sample Claims</span>
        <select
          onChange={(e) => {
            if (!e.target.value) return
            onUseSample(e.target.value)
            e.target.value = ''
          }}
          disabled={loading}
          defaultValue=""
        >
          <option value="" disabled>
            Select a multilingual demo case
          </option>
          {sampleCases.map((sample) => (
            <option key={sample.key} value={sample.key}>
              {sample.label}
            </option>
          ))}
        </select>
      </label>

      {mode === 'text' ? (
        <label className="field">
          <span>Claim Input</span>
          <textarea
            value={input}
            onChange={(e) => onInputChange(e.target.value)}
            rows={7}
            disabled={loading}
            placeholder="Paste suspicious text in Hindi, Tamil, Bengali, Marathi, Telugu, English, or mixed scripts."
            aria-invalid={Boolean(inputError)}
          />
        </label>
      ) : (
        <label className="field">
          <span>Upload Image</span>
          <input
            type="file"
            accept="image/png,image/jpeg,image/webp"
            onChange={(e) => onFileChange(e.target.files?.[0] || null)}
            disabled={loading}
          />
          <small className="field-note">{file ? `Selected: ${file.name}` : 'Supports PNG/JPG/WEBP up to server limits.'}</small>
        </label>
      )}

      {inputError && <p className="inline-error">{inputError}</p>}

      <div className="sticky-actions">
        <button type="button" className="btn btn-secondary" onClick={() => onUseSample('hi_water')} disabled={loading}>
          Try Sample
        </button>
        <button type="button" className="btn btn-primary" onClick={onSubmit} disabled={loading}>
          {loading ? 'Running Verification...' : 'Verify Claim'}
        </button>
      </div>
    </section>
  )
}

export default InputModule
