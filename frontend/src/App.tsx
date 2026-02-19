import { useState, useRef, useEffect } from 'react'
import { chat, clearSession, unloadSession, getSessionHistory, setIdentity, productUpdate } from './api/supervisor'
import type { PendingActionProductUpdate } from './api/supervisor'
import './App.css'

const CHAT_ID = 'default'

function formatChatError(err: unknown): string {
  if (err && typeof err === 'object' && 'response' in err) {
    const ax = err as { response?: { status?: number }; message?: string }
    const status = ax.response?.status
    if (status === 502 || status === 503)
      return '无法连接到后端服务，请确保 Supervisor API 已启动（端口 8000）'
    if (status === 500) return '服务器内部错误，请稍后再试'
    if (status === 404) return '接口不存在，请检查服务配置'
  }
  if (err instanceof Error) {
    if (/network|fetch|ECONNREFUSED/i.test(err.message))
      return '网络连接失败，请确保 Supervisor API 已启动（端口 8000）'
    return err.message
  }
  return '请求失败，请稍后重试'
}

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
  const [userId, setUserId] = useState<string | null>(null)
  const [showLoginModal, setShowLoginModal] = useState(false)
  const [loginRole, setLoginRole] = useState<'customer' | 'staff'>('customer')
  const [loginAccountId, setLoginAccountId] = useState('')
  const [loginError, setLoginError] = useState<string | null>(null)
  const [pendingAction, setPendingAction] = useState<PendingActionProductUpdate | null>(null)
  const [confirmLoading, setConfirmLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const currentUserId = userId || 'guest'

  const handleLogin = async () => {
    const accountId = loginAccountId.trim()
    if (!accountId) {
      setLoginError('请输入账号 ID')
      return
    }
    if (!/^\d+$/.test(accountId)) {
      setLoginError('账号 ID 需为数字（如 10001）')
      return
    }
    setLoginError(null)
    try {
      await setIdentity({
        user_id: accountId,
        chat_id: CHAT_ID,
        role: loginRole,
      })
      setUserId(accountId)
      setRole(loginRole)
      setShowLoginModal(false)
      setLoginAccountId('')
      const { history } = await getSessionHistory(accountId, CHAT_ID)
      if (history?.length) {
        setMessages(
          history.map((m) => ({
            id: crypto.randomUUID(),
            role: m.role as 'user' | 'assistant',
            content: m.content,
            timestamp: new Date(),
          }))
        )
      }
    } catch {
      setLoginError('登录失败，请稍后重试')
    }
  }

  const handleLogout = async () => {
    if (userId) {
      try {
        await unloadSession(userId, CHAT_ID)
      } catch {
        // ignore
      }
    }
    setUserId(null)
    setRole(null)
    setMessages([])
    setError(null)
  }

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
        user_id: currentUserId,
        chat_id: CHAT_ID,
        role: role || undefined,
      })

      if (res.role) setRole(res.role)

      const assistantMessage: Message = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: res.reply,
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, assistantMessage])

      if (res.pending_action?.type === 'product_update') {
        setPendingAction(res.pending_action)
      }
    } catch (err: unknown) {
      const msg = formatChatError(err)
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

  const handleConfirmProductUpdate = async () => {
    if (!pendingAction) return
    setConfirmLoading(true)
    try {
      const payload: { productName: string; price?: number; stock?: number } = {
        productName: pendingAction.productName,
      }
      if (pendingAction.proposed.price !== undefined) payload.price = pendingAction.proposed.price
      if (pendingAction.proposed.stock !== undefined) payload.stock = pendingAction.proposed.stock
      const { message } = await productUpdate(payload)
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: `✅ ${message}`,
          timestamp: new Date(),
        },
      ])
      setPendingAction(null)
    } catch (err) {
      const msg = err instanceof Error ? err.message : '修改失败'
      setError(msg)
    } finally {
      setConfirmLoading(false)
    }
  }

  const handleClear = async () => {
    try {
      await clearSession(currentUserId, CHAT_ID)
      setMessages([])
      setPendingAction(null)
      if (!userId) setRole(null)
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
        <div className="header-actions">
          {userId && (
            <span className="user-badge">
              {role === 'customer' && '顾客'}
              {role === 'staff' && '店员'}
              {!['customer', 'staff'].includes(role || '') && role}
              {' · '}ID: {userId}
            </span>
          )}
          {userId ? (
            <button className="header-btn" onClick={handleLogout} type="button">
              退出
            </button>
          ) : (
            <button
              className="header-btn header-btn--primary"
              onClick={() => setShowLoginModal(true)}
              type="button"
            >
              登录
            </button>
          )}
          <button className="header-btn" onClick={handleClear} type="button">
            新对话
          </button>
        </div>
      </header>

      {pendingAction && (
        <div className="modal-overlay" onClick={() => !confirmLoading && setPendingAction(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3 className="modal-title">确认修改产品</h3>
            <div className="modal-desc">
              <p>产品：{pendingAction.productName}</p>
              <ul style={{ marginTop: 8, paddingLeft: 20 }}>
                {pendingAction.proposed.price !== undefined && (
                  <li>
                    单价：¥{pendingAction.current.price ?? '-'} → ¥{pendingAction.proposed.price}
                  </li>
                )}
                {pendingAction.proposed.stock !== undefined && (
                  <li>
                    库存：{pendingAction.current.stock ?? '-'} → {pendingAction.proposed.stock}
                  </li>
                )}
              </ul>
            </div>
            <div className="modal-buttons">
              <button
                className="modal-btn modal-btn--cancel"
                onClick={() => !confirmLoading && setPendingAction(null)}
                disabled={confirmLoading}
                type="button"
              >
                取消
              </button>
              <button
                className="modal-btn modal-btn--confirm"
                onClick={handleConfirmProductUpdate}
                disabled={confirmLoading}
                type="button"
              >
                {confirmLoading ? '执行中...' : '确认修改'}
              </button>
            </div>
          </div>
        </div>
      )}

      {showLoginModal && (
        <div className="modal-overlay" onClick={() => setShowLoginModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3 className="modal-title">登录</h3>
            <p className="modal-desc">Demo 演示，无需密码</p>
            <div className="modal-form">
              <label>
                身份
                <select
                  value={loginRole}
                  onChange={(e) =>
                    setLoginRole(e.target.value as 'customer' | 'staff')
                  }
                >
                  <option value="customer">用户</option>
                  <option value="staff">店员</option>
                </select>
              </label>
              <label>
                账号 ID
                <input
                  type="text"
                  placeholder="请输入数字，如 10001"
                  value={loginAccountId}
                  onChange={(e) => setLoginAccountId(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleLogin()}
                />
              </label>
              {loginError && <div className="modal-error">{loginError}</div>}
              <div className="modal-buttons">
                <button
                  className="modal-btn modal-btn--cancel"
                  onClick={() => setShowLoginModal(false)}
                  type="button"
                >
                  取消
                </button>
                <button
                  className="modal-btn modal-btn--confirm"
                  onClick={handleLogin}
                  type="button"
                >
                  登录
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      <main className="chat">
        <div className="messages">
          {messages.length === 0 && (
            <div className="welcome">
              <p>你好～ 我是云边奶茶铺的智能助手。</p>
              {userId ? (
                <>
                  <p>已登录为【{role === 'customer' ? '用户' : '店员'}】，账号 {userId}。</p>
                  <p>可以点单、查询菜单、查看订单记录～</p>
                </>
              ) : (
                <>
                  <p>未登录可浏览菜单和价格，登录后可下单并查看订单记录。</p>
                  <p>点击右上角「登录」选择身份并输入账号 ID。</p>
                </>
              )}
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
