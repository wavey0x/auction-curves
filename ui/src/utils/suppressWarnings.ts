// Suppress specific noisy dev warnings without changing app behavior
// Only active in development
if (import.meta.env.DEV) {
  const patterns = [
    /React Router Future Flag Warning/i,
    /v7_startTransition/i,
    /startTransition in v7/i,
  ]

  const shouldSuppress = (args: any[]): boolean => {
    try {
      const msg = args.map(String).join(' ')
      return patterns.some((re) => re.test(msg))
    } catch {
      return false
    }
  }

  const origWarn = console.warn
  const origError = console.error

  console.warn = (...args: any[]) => {
    if (shouldSuppress(args)) return
    origWarn.apply(console, args)
  }

  console.error = (...args: any[]) => {
    if (shouldSuppress(args)) return
    origError.apply(console, args)
  }
}

