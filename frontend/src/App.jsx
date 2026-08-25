import { Link, Route, Routes } from 'react-router-dom'
import { LangProvider, useLang } from './i18n.jsx'
import Dashboard from './pages/Dashboard.jsx'
import EventDetail from './pages/EventDetail.jsx'
import SmsGenerator from './pages/SmsGenerator.jsx'

function Topbar() {
  const { lang, setLang, t } = useLang()
  return (
    <header className="topbar">
      <Link to="/" className="brand">📈 {t('brand')}</Link>
      <nav>
        <Link to="/">{t('dashboard')}</Link>
        <Link to="/sms">{t('smsGenerator')}</Link>
        <div className="lang-switch">
          <button className={lang === 'en' ? 'active' : ''} onClick={() => setLang('en')}>EN</button>
          <button className={lang === 'zh' ? 'active' : ''} onClick={() => setLang('zh')}>中文</button>
        </div>
      </nav>
    </header>
  )
}

export default function App() {
  return (
    <LangProvider>
      <div className="app">
        <Topbar />
        <main>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/events/:id" element={<EventDetail />} />
            <Route path="/sms" element={<SmsGenerator />} />
          </Routes>
        </main>
      </div>
    </LangProvider>
  )
}
