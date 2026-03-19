import React, { useState } from 'react'
import Chat from './Chat'
import Dashboard from './Dashboard'

/**
 * App layout with Dashboard ↔ AI Chat view switching.
 *
 * "Ask AI" buttons on dashboard charts send the user to
 * the chat view with a pre-filled question — demonstrating
 * how the AI layer integrates into the existing dashboard.
 */
export default function App() {
  const [view, setView] = useState('dashboard')
  const [prefillMessage, setPrefillMessage] = useState('')

  const handleAskAI = (question) => {
    setPrefillMessage(question)
    setView('chat')
  }

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="sidebar-logo">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M12 2C8 6 4 10 4 14a8 8 0 0016 0c0-4-4-8-8-12z" />
            <path d="M12 22v-8" />
            <path d="M8 18l4-4 4 4" />
          </svg>
          Vintality
        </div>

        <nav className="sidebar-nav">
          <a
            href="#"
            className={view === 'dashboard' ? 'active' : ''}
            onClick={(e) => { e.preventDefault(); setView('dashboard') }}
          >
            Dashboard
          </a>
          <a
            href="#"
            className={view === 'chat' ? 'active' : ''}
            onClick={(e) => { e.preventDefault(); setView('chat') }}
          >
            AI Assistant
          </a>
        </nav>

        <div className="sidebar-farm">
          <div className="farm-name">Naramata Hills Vineyard</div>
          <div className="farm-detail">
            Naramata Bench, BC<br />
            4 blocks · 7.2 ha<br />
            Season: Post-veraison
          </div>
        </div>
      </aside>

      <main className="main-content">
        <div className="top-bar">
          <h1>{view === 'dashboard' ? 'Farm Dashboard' : 'AI Assistant'}</h1>
          {view === 'dashboard' && <span className="badge live">Live</span>}
          {view === 'chat' && <span className="badge">Beta</span>}
          <div className="top-bar-toggle">
            <button
              className={`toggle-btn ${view === 'dashboard' ? 'active' : ''}`}
              onClick={() => setView('dashboard')}
            >
              Dashboard
            </button>
            <button
              className={`toggle-btn ${view === 'chat' ? 'active' : ''}`}
              onClick={() => setView('chat')}
            >
              AI Chat
            </button>
          </div>
        </div>

        {view === 'dashboard' ? (
          <Dashboard onAskAI={handleAskAI} />
        ) : (
          <Chat
            prefillMessage={prefillMessage}
            onPrefillConsumed={() => setPrefillMessage('')}
          />
        )}
      </main>
    </div>
  )
}