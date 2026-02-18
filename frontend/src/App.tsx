import { useState, useRef, useEffect } from 'react'
import { chat, clearSession } from './api/supervisor'
import './App.css'

const USER_ID = 'user_001'
const CHAT_ID = 'default'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
}

function App() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [role, setRole] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSend = async () => {
    const text = input.trim()
    if (!text || loading) return

    setInput('')
    setError(null)

    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content: text,
      timestamp: new Date(),
    }
    setMessages((prev) => [...prev, userMessage])
    setLoading(true)

    try {
      const res = await chat({
        message: text,
        user_id: USER_ID,
        chat_id: CHAT_ID,
      })

      if (res.role) setRole(res.role)

      const assistantMessage: Message = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: res.reply,
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, assistantMessage])
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : '请求失败，请稍后重试'
      setError(msg)
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: `抱歉，出了点问题：${msg}`,
          timestamp: new Date(),
        },
      ])
    } finally {
      setLoading(false)
    }
  }

  const handleClear = async () => {
    try {
      await clearSession(USER_ID, CHAT_ID)
      setMessages([])
      setRole(null)
      setError(null)
    } catch {
      setError('清空会话失败')
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="app">
      <header className="header">
        <h1 className="title">云边奶茶铺</h1>
        <p className="subtitle">智能点单 · 产品咨询 · 反馈服务</p>
        {role && (
          <span className="role-badge">
            {role === 'customer' && '顾客'}
            {role === 'staff' && '店员'}
            {role === 'admin' && '管理员'}
            {!['customer', 'staff', 'admin'].includes(role) && role}
          </span>
        )}
        <button className="clear-btn" onClick={handleClear} type="button">
          新对话
        </button>
      </header>

      <main className="chat">
        <div className="messages">
          {messages.length === 0 && (
            <div className="welcome">
              <p>你好～ 我是云边奶茶铺的智能助手。</p>
              <p>请先告诉我你的身份：顾客、店员或管理员。</p>
              <p>确认身份后，我可以帮你点单、咨询产品或处理反馈～</p>
            </div>
          )}
          {messages.map((m) => (
            <div key={m.id} className={`message message--${m.role}`}>
              <div className="message-bubble">
                <span className="message-content">{m.content}</span>
              </div>
            </div>
          ))}
          {loading && (
            <div className="message message--assistant">
              <div className="message-bubble message-bubble--typing">
                <span className="typing-dot" />
                <span className="typing-dot" />
                <span className="typing-dot" />
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {error && <div className="error-bar">{error}</div>}

        <div className="input-area">
          <textarea
            className="input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="输入消息，按 Enter 发送..."
            rows={1}
            disabled={loading}
          />
          <button
            className="send-btn"
            onClick={handleSend}
            disabled={loading || !input.trim()}
            type="button"
          >
            发送
          </button>
        </div>
      </main>
    </div>
  )
}

export default App
