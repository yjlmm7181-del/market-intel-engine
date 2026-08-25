import { Link, Route, Routes } from 'react-router-dom'
import Dashboard from './pages/Dashboard.jsx'
import EventDetail from './pages/EventDetail.jsx'
import SmsGenerator from './pages/SmsGenerator.jsx'

export default function App() {
  return (
    <div className="app">
      <header className="topbar">
        <Link to="/" className="brand">📈 Market Intel Engine</Link>
        <nav>
          <Link to="/">Dashboard</Link>
          <Link to="/sms">SMS Generator</Link>
        </nav>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/events/:id" element={<EventDetail />} />
          <Route path="/sms" element={<SmsGenerator />} />
        </Routes>
      </main>
    </div>
  )
}
