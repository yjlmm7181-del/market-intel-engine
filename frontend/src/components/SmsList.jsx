import { useLang } from '../i18n.jsx'

export default function SmsList({ messages }) {
  const { t } = useLang()
  return (
    <div className="sms-list">
      {messages.map((m) => (
        <div className="sms" key={m.id ?? m.version}>
          <div className="sms-top">
            <span className="version">{t('version')} {m.version}</span>
            <span className="cta">{m.cta}</span>
          </div>
          <p className="sms-body">{m.body}</p>
        </div>
      ))}
    </div>
  )
}
