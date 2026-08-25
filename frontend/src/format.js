export const fmtPct = (v) => (v == null ? '—' : `${v > 0 ? '+' : ''}${v.toFixed(2)}%`)

export const fmtPrice = (v) => (v == null ? '—' : v.toFixed(2))

export const pctClass = (v) => (v == null ? '' : v >= 0 ? 'up' : 'down')
