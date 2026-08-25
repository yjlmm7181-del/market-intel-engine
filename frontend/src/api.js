async function fetchJSON(path, options) {
  const res = await fetch(path, options)
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json()
}

export const api = {
  overview: () => fetchJSON('/api/market/overview'),
  event: (id) => fetchJSON(`/api/events/${id}`),
  generateSms: (id) => fetchJSON(`/api/events/${id}/generate-sms`, { method: 'POST' }),
  listSms: () => fetchJSON('/api/sms'),
  regenerateSms: (id) => fetchJSON(`/api/sms/${id}/regenerate`, { method: 'POST' }),
}
