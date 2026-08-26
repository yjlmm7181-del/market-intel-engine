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

function RefreshIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
         stroke="#8b93a7" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 12a9 9 0 1 1-2.64-6.36L21 8" />
      <path d="M21 3v5h-5" />
    </svg>
  )
}

function SmsCard({ m, onRefresh }) {
  const { t } = useLang()
  const [copied, setCopied] = useState(false)

  async function copy() {
    const text = m.body_zh ? `${m.body_zh}\n${m.body}` : m.body
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
          {onRefresh && (
            <button className="copy-btn" onClick={() => onRefresh(m.version)} title={t('refresh')}>
              <RefreshIcon />
            </button>
          )}
        </div>
      </div>
      <p className="sms-body zh">{m.body_zh || m.body}</p>
      <p className="sms-body">{m.body}</p>
    </div>
  )
}

export default function SmsList({ messages, onRefresh }) {
  return (
    <div className="sms-list">
      {messages.map((m) => (
        <SmsCard key={m.id ?? m.version} m={m} onRefresh={onRefresh} />
      ))}
    </div>
  )
}
