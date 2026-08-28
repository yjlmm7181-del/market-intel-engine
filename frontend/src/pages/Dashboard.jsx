import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api.js'
import { fmtPct, fmtPrice, pctClass } from '../format.js'
import { useLang } from '../i18n.jsx'
import SmsList from '../components/SmsList.jsx'

export default function Dashboard() {
  const { t } = useLang()
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [smsByEvent, setSmsByEvent] = useState({})
  const [loadingSms, setLoadingSms] = useState(null)
  const [style, setStyle] = useState('hook')

  useEffect(() => {
    let cancelled = false
    async function load(attemptsLeft) {
      try {
        const d = await api.overview()
        if (!cancelled) setData(d)
      } catch (e) {
        if (attemptsLeft > 0 && !cancelled) {
          setTimeout(() => load(attemptsLeft - 1), 3000)
        } else if (!cancelled) {
          setError(e.message)
        }
      }
    }
    load(2)
    return () => { cancelled = true }
  }, [])

  async function generate(id) {
    setLoadingSms(id)
    try {
      const msgs = await api.generateSms(id, style)
      setSmsByEvent((s) => ({ ...s, [id]: msgs }))
    } catch (e) {
      setError(e.message)
    } finally {
      setLoadingSms(null)
    }
  }

  if (error) return <div className="state error">{t('failed')}: {error}</div>
  if (!data) return <div className="state">{t('loading')}</div>

  const topEvents = data.events.slice(0, 10)

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
          <h2>{t('movers')}</h2>
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
          <h2>{t('news')}</h2>
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
        <h2>{t('topEvents')}</h2>
        {topEvents.map((e) => (
          <div className="card event" key={e.id}>
            <div className="event-head">
              <span className="event-title">🔥 {e.title}</span>
              <span className="heat">{t('heat')} {e.heat_score}</span>
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
                {loadingSms === e.id ? t('generating') : t('generateSms')}
              </button>
              <div className="switch">
                <button className={style === 'standard' ? 'active' : ''} onClick={() => setStyle('standard')}>{t('styleStandard')}</button>
                <button className={style === 'hook' ? 'active' : ''} onClick={() => setStyle('hook')}>{t('styleHook')}</button>
                <button className={style === 'urgent' ? 'active' : ''} onClick={() => setStyle('urgent')}>{t('styleUrgent')}</button>
              </div>
              <Link className="link" to={`/events/${e.id}`}>{t('details')}</Link>
            </div>
            {smsByEvent[e.id] && <SmsList messages={smsByEvent[e.id]} />}
          </div>
        ))}
      </section>
    </div>
  )
}
