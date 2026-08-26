async function fetchJSON(path, options) {
  const res = await fetch(path, options)
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json()
}

export const api = {
  overview: () => fetchJSON('/api/market/overview'),
  event: (id) => fetchJSON(`/api/events/${id}`),
  generateSms: (id, style) => fetchJSON(`/api/events/${id}/generate-sms?style=${style || 'hook'}`, { method: 'POST' }),
  generateSmsDeck: (id, style) => fetchJSON(`/api/events/${id}/generate-sms-deck?style=${style || 'hook'}`, { method: 'POST' }),
  refreshSmsCard: (id, deckId, version, style) => fetchJSON(`/api/events/${id}/sms/${version}/refresh?deck_id=${deckId}&style=${style || 'hook'}`, { method: 'POST' }),
  refreshSmsAll: (id, style) => fetchJSON(`/api/events/${id}/sms/refresh-all?style=${style || 'hook'}`, { method: 'POST' }),
  listSms: () => fetchJSON('/api/sms'),
  regenerateSms: (id) => fetchJSON(`/api/sms/${id}/regenerate`, { method: 'POST' }),
}
