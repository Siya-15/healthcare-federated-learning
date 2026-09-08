import { useCallback, useEffect, useRef, useState } from 'react'

// Generic fetch-on-mount hook for the service layer.
// `fn` receives { signal } and returns a promise. Re-runs when `deps` change
// or `reload()` is called. `data._mock` (set by services/api.js) means the
// payload is sample data because the backend was unreachable.
export function useApi(fn, deps = []) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)
  const [nonce, setNonce] = useState(0)
  const fnRef = useRef(fn)
  fnRef.current = fn

  const reload = useCallback(() => setNonce((n) => n + 1), [])

  useEffect(() => {
    const controller = new AbortController()
    setLoading(true)
    setError(null)
    Promise.resolve(fnRef.current({ signal: controller.signal }))
      .then((d) => {
        if (!controller.signal.aborted) setData(d)
      })
      .catch((e) => {
        if (e?.name === 'AbortError') return
        setError(e)
        setData(null)
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })
    return () => controller.abort()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, nonce])

  return { data, error, loading, reload, isMock: Boolean(data?._mock) }
}
