function BrandLogo({ title = 'VeritasGuard', subtitle = '', className = '' }) {
  return (
    <div className={`brand-lockup ${className}`.trim()}>
      <div className="brand-mark-shell" aria-hidden="true">
        <svg
          className="brand-mark-svg"
          viewBox="0 0 128 128"
          role="img"
          aria-label="VeritasGuard logo mark"
        >
          <defs>
            <linearGradient id="vgShieldGradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#ffd66d" />
              <stop offset="55%" stopColor="#ff9c4a" />
              <stop offset="100%" stopColor="#f04543" />
            </linearGradient>
            <linearGradient id="vgCheckGradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#ffca69" />
              <stop offset="65%" stopColor="#ff7a4d" />
              <stop offset="100%" stopColor="#ff4f45" />
            </linearGradient>
          </defs>
          <path
            d="M20 22h88v36c0 30-19 54-44 67-25-13-44-37-44-67V22z"
            fill="none"
            stroke="url(#vgShieldGradient)"
            strokeWidth="5"
            strokeLinejoin="round"
          />
          <path
            d="M36 70c11-3 18 5 23 17 16-30 34-44 53-45-24 5-40 18-53 47H47c-4-9-8-16-11-19z"
            fill="url(#vgCheckGradient)"
          />
          <path d="M58 88c14-28 30-42 50-47" fill="none" stroke="#1a263a" strokeWidth="2.2" />
        </svg>
      </div>
      <div className="brand-copy">
        <strong className="brand-wordmark">{title}</strong>
        {subtitle ? <span>{subtitle}</span> : null}
      </div>
    </div>
  )
}

export default BrandLogo
