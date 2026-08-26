import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { useLang } from '../i18n.jsx'
import SmsList from '../components/SmsList.jsx'

export default function SmsGenerator() {
  const { t } = useLang()
  const [events, setEvents] = useState([])
  const [selected, setSelected] = useState(null)
  const [deck, setDeck] = useState(null) // { deck_id, messages }
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    api.overview()
      .then((d) => {
        setEvents(d.events.slice(0, 10))
        if (d.events.length) setSelected(d.events[0].id)
      })
      .catch((e) => setError(e.message))
  }, [])

  useEffect(() => {
    if (selected) loadDeck()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selected])

  async function loadDeck() {
    setLoading(true)
    try {
      setDeck(await api.generateSmsDeck(selected))
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  async function refreshOne(version) {
    if (!deck) return
    try {
      const msg = await api.refreshSmsCard(selected, deck.deck_id, version)
      setDeck((d) => ({ ...d, messages: d.messages.map((m) => (m.version === version ? msg : m)) }))
    } catch (e) {
      setError(e.message)
    }
  }

  async function refreshAll() {
    await loadDeck()
  }

  return (
    <div>
      <h1>{t('smsGenerator')}</h1>
      {error && <div className="state error">{error}</div>}

      <div className="card">
        <div className="row">
          <select value={selected ?? ''} onChange={(e) => setSelected(Number(e.target.value))}>
            {events.map((e) => (
              <option key={e.id} value={e.id}>{e.title} ({t('heat')} {e.heat_score})</option>
            ))}
          </select>
          <button onClick={refreshAll} disabled={loading || !selected}>
            {loading ? t('generating') : t('refreshAll')}
          </button>
        </div>
        {deck && <SmsList messages={deck.messages} onRefresh={refreshOne} />}
      </div>
    </div>
  )
}
