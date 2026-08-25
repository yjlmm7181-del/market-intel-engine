import { useState } from 'react'
import { useLang } from '../i18n.jsx'

function CopyIcon({ copied }) {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
         stroke={copied ? '#2fd6a4' : '#8b93a7'} strokeWidth="2"
         strokeLinecap="round" strokeLinejoin="round">
      <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
    </svg>
  )
}

function SmsCard({ m, showZh }) {
  const { t } = useLang()
  const [copied, setCopied] = useState(false)

  async function copy() {
    const text = showZh && m.body_zh ? `${m.body}\n${m.body_zh}` : m.body
    try {
      await navigator.clipboard.writeText(text)
    } catch (e) {
      const ta = document.createElement('textarea')
      ta.value = text
      document.body.appendChild(ta)
      ta.select()
      document.execCommand('copy')
      document.body.removeChild(ta)
    }
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  return (
    <div className="sms">
      <div className="sms-top">
        <span className="version">{t('version')} {m.version}</span>
        <div className="sms-actions">
          <span className="cta">{m.cta}</span>
          <button className="copy-btn" onClick={copy} title={copied ? '✓' : 'Copy'}>
            <CopyIcon copied={copied} />
          </button>
        </div>
      </div>
      <p className="sms-body">{m.body}</p>
      {showZh && m.body_zh && <p className="sms-body zh">{m.body_zh}</p>}
    </div>
  )
}

export default function SmsList({ messages, showZh = false }) {
  return (
    <div className="sms-list">
      {messages.map((m) => (
        <SmsCard key={m.id ?? m.version} m={m} showZh={showZh} />
      ))}
    </div>
  )
}
