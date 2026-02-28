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
