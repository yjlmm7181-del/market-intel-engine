import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api.js'
import { fmtPct, pctClass } from '../format.js'
import { useLang } from '../i18n.jsx'
import SmsList from '../components/SmsList.jsx'

export default function EventDetail() {
  const { id } = useParams()
  const { t } = useLang()
  const [event, setEvent] = useState(null)
  const [sms, setSms] = useState(null)
  const [style, setStyle] = useState('hook')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    api.event(id).then(setEvent).catch((e) => setError(e.message))
  }, [id])

  async function generate() {
    setLoading(true)
    try {
      setSms(await api.generateSms(id, style))
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  if (error) return <div className="state error">{error}</div>
  if (!event) return <div className="state">{t('loadingShort')}</div>

  return (
    <div>
      <Link to="/" className="link">{t('back')}</Link>
      <div className="card event">
        <div className="event-head">
          <span className="event-title">🔥 {event.title}</span>
          <span className="heat">{t('heat')} {event.heat_score}</span>
        </div>
        <div className="event-meta">
          <span>{event.index_key.toUpperCase()}</span>
          <span className={pctClass(event.index_change)}>{fmtPct(event.index_change)}</span>
        </div>
        <p className="summary">{event.ai_summary}</p>

        <h3>{t('stocks')}</h3>
        <ul className="movers">
          {event.stocks.map((s) => (
            <li key={s.symbol}>
              <span className="sym">{s.symbol}</span>
              <span className="name">{s.name}</span>
              <span className={pctClass(s.change_rate)}>{fmtPct(s.change_rate)}</span>
            </li>
          ))}
        </ul>

        <h3>{t('news')}</h3>
        <ul className="news">
          {event.news.map((n, i) => (
            <li key={i}>
              <a href={n.url} target="_blank" rel="noreferrer">{n.title}</a>
            </li>
          ))}
        </ul>

        <div className="actions">
          <button onClick={generate} disabled={loading}>
            {loading ? t('generating') : t('generateSms')}
          </button>
          <div className="switch">
            <button className={style === 'standard' ? 'active' : ''} onClick={() => setStyle('standard')}>{t('styleStandard')}</button>
            <button className={style === 'hook' ? 'active' : ''} onClick={() => setStyle('hook')}>{t('styleHook')}</button>
            <button className={style === 'urgent' ? 'active' : ''} onClick={() => setStyle('urgent')}>{t('styleUrgent')}</button>
          </div>
        </div>
        {sms && <SmsList messages={sms} />}
      </div>
    </div>
  )
}
