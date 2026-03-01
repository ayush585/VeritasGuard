export function prettyPercent(value) {
  const num = Number(value || 0)
  if (Number.isNaN(num)) return '0%'
  return `${Math.round(num * 100)}%`
}

export function prettyMs(value) {
  const num = Number(value || 0)
  if (Number.isNaN(num) || num <= 0) return '--'
  if (num >= 1000) return `${(num / 1000).toFixed(1)}s`
  return `${Math.round(num)}ms`
}

export function titleCase(value) {
  return String(value || '')
    .replace(/[_-]+/g, ' ')
    .trim()
    .replace(/\b\w/g, (m) => m.toUpperCase())
}

export function sourceLabel(provider) {
  const map = {
    mistral_web_search: 'Mistral Web Search',
    tavily_search_fallback: 'Tavily Fallback',
    local_known_hoax_references: 'Local Trusted References',
    none: 'No External Search',
  }
  return map[provider] || titleCase(provider || 'none')
}

export function domainFromUrl(rawUrl) {
  if (!rawUrl) return ''
  try {
    const parsed = new URL(rawUrl)
    return parsed.hostname.replace('www.', '')
  } catch {
    return ''
  }
}

export function summarizeWarnings(warnings = []) {
  if (!Array.isArray(warnings) || warnings.length === 0) return []
  return warnings.map((warning) => {
    const text = String(warning)
    if (text.includes('Source retrieval degraded')) {
      return 'Web evidence retrieval was limited; local verified references were used.'
    }
    if (text.includes('timed out')) {
      return 'Some agents timed out; verdict used available high-confidence signals.'
    }
    return text
  })
}
