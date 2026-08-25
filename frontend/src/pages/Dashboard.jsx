import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api.js'
import { fmtPct, fmtPrice, pctClass } from '../format.js'
import SmsList from '../components/SmsList.jsx'

export default function Dashboard() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [smsByEvent, setSmsByEvent] = useState({})
  const [loadingSms, setLoadingSms] = useState(null)

  useEffect(() => {
    api.overview().then(setData).catch((e) => setError(e.message))
  }, [])

  async function generate(id) {
    setLoadingSms(id)
    try {
      const msgs = await api.generateSms(id)
      setSmsByEvent((s) => ({ ...s, [id]: msgs }))
    } catch (e) {
      setError(e.message)
    } finally {
      setLoadingSms(null)
    }
  }

  if (error) return <div className="state error">Failed to load: {error}</div>
  if (!data) return <div className="state">Loading market data… (first load can take ~20s)</div>

  const topEvents = data.events.slice(0, 3)

  return (
    <div>
      <section className="indexes">
        {data.indexes.map((i) => (
          <div className="card index-card" key={i.key}>
            <div className="index-name">{i.name}</div>
            <div className="index-price">{fmtPrice(i.last_price)}</div>
            <div className={`index-change ${pctClass(i.change_rate)}`}>{fmtPct(i.change_rate)}</div>
          </div>
        ))}
      </section>

      <div className="grid">
        <section className="card">
          <h2>Today's Movers</h2>
          <ul className="movers">
            {data.movers.map((m) => (
              <li key={m.symbol}>
                <span className="sym">{m.symbol}</span>
                <span className="name">{m.name}</span>
                <span className={pctClass(m.change_rate)}>{fmtPct(m.change_rate)}</span>
              </li>
            ))}
          </ul>
        </section>

        <section className="card">
          <h2>Related News</h2>
          <ul className="news">
            {data.news.slice(0, 12).map((n) => (
              <li key={n.news_id}>
                <a href={n.url} target="_blank" rel="noreferrer">{n.title}</a>
              </li>
            ))}
          </ul>
        </section>
      </div>

      <section>
        <h2>Top Market Events</h2>
        {topEvents.map((e) => (
          <div className="card event" key={e.id}>
            <div className="event-head">
              <span className="event-title">🔥 {e.title}</span>
              <span className="heat">Heat {e.heat_score}</span>
            </div>
            <div className="event-meta">
              <span>{e.index_key.toUpperCase()}</span>
              <span className={pctClass(e.index_change)}>{fmtPct(e.index_change)}</span>
              {e.stocks.slice(0, 4).map((s) => (
                <span key={s.symbol} className="chip">
                  {s.symbol} <span className={pctClass(s.change_rate)}>{fmtPct(s.change_rate)}</span>
                </span>
              ))}
            </div>
            <p className="summary">{e.ai_summary}</p>
            <div className="actions">
              <button onClick={() => generate(e.id)} disabled={loadingSms === e.id}>
                {loadingSms === e.id ? 'Generating…' : 'GENERATE SMS'}
              </button>
              <Link className="link" to={`/events/${e.id}`}>Details →</Link>
            </div>
            {smsByEvent[e.id] && <SmsList messages={smsByEvent[e.id]} />}
          </div>
        ))}
      </section>
    </div>
  )
}
