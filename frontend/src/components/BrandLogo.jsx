function BrandLogo({ title = 'VeritasGuard', subtitle = '', className = '' }) {
  return (
    <div className={`brand-lockup ${className}`.trim()}>
      <svg
        className="brand-mark-svg"
        viewBox="0 0 128 128"
        role="img"
        aria-label="VeritasGuard logo mark"
      >
        <defs>
          <linearGradient id="vgGradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#f6ca6e" />
            <stop offset="55%" stopColor="#f28f4b" />
            <stop offset="100%" stopColor="#de5242" />
          </linearGradient>
        </defs>
        <path
          d="M24 20h80v40c0 24-16 44-40 56C40 104 24 84 24 60V20z"
          fill="none"
          stroke="url(#vgGradient)"
          strokeWidth="8"
          strokeLinejoin="round"
        />
        <path
          d="M38 66c10 0 16 8 23 22 16-31 35-43 52-45-25-2-42 10-55 34-4-9-10-18-20-11z"
          fill="url(#vgGradient)"
        />
      </svg>
      <div className="brand-copy">
        <strong>{title}</strong>
        {subtitle ? <span>{subtitle}</span> : null}
      </div>
    </div>
  )
}

export default BrandLogo
