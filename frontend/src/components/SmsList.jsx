export default function SmsList({ messages }) {
  return (
    <div className="sms-list">
      {messages.map((m) => (
        <div className="sms" key={m.id ?? m.version}>
          <div className="sms-top">
            <span className="version">Version {m.version}</span>
            <span className="cta">{m.cta}</span>
          </div>
          <p className="sms-body">{m.body}</p>
        </div>
      ))}
    </div>
  )
}
