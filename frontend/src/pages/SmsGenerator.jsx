import { useEffect, useState } from 'react'
import { api } from '../api.js'
import SmsList from '../components/SmsList.jsx'

export default function SmsGenerator() {
  const [events, setEvents] = useState([])
  const [selected, setSelected] = useState(null)
  const [sms, setSms] = useState(null)
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    api.overview()
      .then((d) => {
        setEvents(d.events.slice(0, 3))
        if (d.events.length) setSelected(d.events[0].id)
      })
      .catch((e) => setError(e.message))
    api.listSms().then(setHistory).catch(() => {})
  }, [])

  async function generate() {
    if (!selected) return
    setLoading(true)
    try {
      setSms(await api.generateSms(selected))
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  async function regen(id) {
    try {
      setSms([await api.regenerateSms(id)])
    } catch (e) {
      setError(e.message)
    }
  }

  return (
    <div>
      <h1>SMS Generator</h1>
      {error && <div className="state error">{error}</div>}

      <div className="card">
        <label>Market Event</label>
        <div className="row">
          <select value={selected ?? ''} onChange={(e) => setSelected(Number(e.target.value))}>
            {events.map((e) => (
              <option key={e.id} value={e.id}>{e.title} (Heat {e.heat_score})</option>
            ))}
          </select>
          <button onClick={generate} disabled={loading || !selected}>
            {loading ? 'Generating…' : 'GENERATE SMS'}
          </button>
        </div>
        {sms && <SmsList messages={sms} />}
      </div>

      <div className="card">
        <h2>History</h2>
        {history.length === 0 && <p className="muted">No messages generated yet.</p>}
        {history.map((m) => (
          <div className="sms" key={m.id}>
            <div className="sms-top">
              <span className="version">V{m.version}</span>
              <span className="cta">{m.cta}</span>
            </div>
            <p className="sms-body">{m.body}</p>
            <button className="ghost" onClick={() => regen(m.id)}>Regenerate</button>
          </div>
        ))}
      </div>
    </div>
  )
}
