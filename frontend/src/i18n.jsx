import { createContext, useContext, useState } from 'react'

const translations = {
  en: {
    brand: 'Market Intel Engine',
    dashboard: 'Dashboard',
    smsGenerator: 'SMS Generator',
    movers: "Today's Movers",
    news: 'Related News',
    topEvents: 'Top Market Events',
    heat: 'Heat',
    generateSms: 'GENERATE SMS',
    generating: 'Generating…',
    details: 'Details →',
    back: '← Back to Dashboard',
    stocks: 'Stocks',
    loading: 'Loading market data… (first load can take ~20s)',
    loadingShort: 'Loading…',
    failed: 'Failed to load',
    marketEvent: 'Market Event',
    history: 'History',
    noMessages: 'No messages generated yet.',
    regenerate: 'Regenerate',
    bilingual: 'Bilingual (EN/中文)',
    style: 'Style',
    styleStandard: 'Standard',
    styleHook: 'Hook',
    styleUrgent: 'Urgent',
    refresh: 'Refresh',
    refreshAll: 'Refresh All',
    version: 'Version',
  },
  zh: {
    brand: '市场情报引擎',
    dashboard: '仪表盘',
    smsGenerator: '短信生成器',
    movers: '今日上涨股票',
    news: '相关新闻',
    topEvents: '热门市场事件',
    heat: '热度',
    generateSms: '生成短信',
    generating: '生成中…',
    details: '详情 →',
    back: '← 返回仪表盘',
    stocks: '相关股票',
    loading: '正在加载行情数据…（首次约 20 秒）',
    loadingShort: '加载中…',
    failed: '加载失败',
    marketEvent: '市场事件',
    history: '历史记录',
    noMessages: '还没有生成短信。',
    regenerate: '重新生成',
    bilingual: '中英文对照',
    style: '风格',
    styleStandard: '简洁',
    styleHook: '钩子',
    styleUrgent: '急迫',
    refresh: '刷新',
    refreshAll: '全部刷新',
    version: '版本',
  },
}

const LangContext = createContext({ lang: 'en', setLang: () => {}, t: (k) => k })

export function LangProvider({ children }) {
  const [lang, setLang] = useState('zh')
  const t = (key) => translations[lang]?.[key] ?? translations.en[key] ?? key
  return (
    <LangContext.Provider value={{ lang, setLang, t }}>
      {children}
    </LangContext.Provider>
  )
}

export function useLang() {
  return useContext(LangContext)
}
