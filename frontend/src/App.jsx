import { useEffect, useMemo, useState } from 'react'
import LandingPage from './routes/LandingPage'
import VerifyPage from './routes/VerifyPage'

function App() {
  const [path, setPath] = useState(window.location.pathname || '/')

  useEffect(() => {
    const onPopState = () => setPath(window.location.pathname || '/')
    window.addEventListener('popstate', onPopState)
    return () => window.removeEventListener('popstate', onPopState)
  }, [])

  const navigate = (nextPath) => {
    if (!nextPath || nextPath === path) return
    window.history.pushState({}, '', nextPath)
    setPath(nextPath)
  }

  const screen = useMemo(() => {
    if (path === '/verify') return <VerifyPage navigate={navigate} />
    return <LandingPage navigate={navigate} />
  }, [path])

  return screen
}

export default App
