import '@testing-library/jest-dom'

if (!global.URL.createObjectURL) {
  global.URL.createObjectURL = () => 'blob:mock-url'
}

if (!global.URL.revokeObjectURL) {
  global.URL.revokeObjectURL = () => {}
}

if (!window.HTMLMediaElement.prototype.play) {
  window.HTMLMediaElement.prototype.play = () => Promise.resolve()
}

if (!navigator.clipboard) {
  navigator.clipboard = {
    writeText: () => Promise.resolve(),
  }
}

if (!window.matchMedia) {
  window.matchMedia = (query) => ({
    matches: query === '(prefers-reduced-motion: reduce)',
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  })
}
