import { useLayoutEffect } from 'react'
import { gsap } from 'gsap'

function prefersReducedMotion() {
  if (typeof window === 'undefined' || !window.matchMedia) return false
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

export function useGsapContext(scopeRef, builder, deps = []) {
  useLayoutEffect(() => {
    if (!scopeRef?.current || prefersReducedMotion()) return undefined
    const ctx = gsap.context(builder, scopeRef)
    return () => ctx.revert()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)
}

export { gsap }
