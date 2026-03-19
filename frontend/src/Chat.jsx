import React, { useState, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'

const EXAMPLE_QUERIES = [
  "Is it safe to irrigate Block 5 today?",
  "Why is PM risk spiking on my Pinot Noir?",
  "Which blocks need attention?",
  "Check the sensors in Block B9",
  "Is there a spray window coming up?",
  "What's the soil moisture trend for B5?",
]

/**
 * Chat component with SSE streaming.
 *
 * Connects to POST /api/chat/stream and processes events:
 * - text: append to current assistant message (streaming effect)
 * - tool_call: show "Querying [tool]..." indicator
 * - tool_result: update indicator to "Done"
 * - done: mark response as complete
 *
 * Multi-turn: sends full conversation_history with each request
 * so Claude maintains context across the session.
 */
export default function Chat({ prefillMessage, onPrefillConsumed }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [toolActivity, setToolActivity] = useState([])
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)

  // Conversation history in Claude's message format
  const conversationHistory = useRef([])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, toolActivity])

  // Handle prefill from dashboard "Ask AI" buttons
  useEffect(() => {
    if (prefillMessage && !isLoading) {
      sendMessage(prefillMessage)
      if (onPrefillConsumed) onPrefillConsumed()
    }
  }, [prefillMessage])

  const sendMessage = async (text) => {
    if (!text.trim() || isLoading) return

    const userMessage = text.trim()
    setInput('')
    setIsLoading(true)
    setToolActivity([])

    // Add user message to UI
    setMessages(prev => [...prev, { role: 'user', content: userMessage }])

    // Add placeholder for assistant response
    setMessages(prev => [...prev, { role: 'assistant', content: '', streaming: true }])

    try {
      // Use fetch with ReadableStream for SSE
      const response = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: userMessage,
          conversation_history: conversationHistory.current,
        }),
      })

      if (!response.ok) throw new Error(`HTTP ${response.status}`)

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let accumulatedText = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })

        // Parse SSE events from buffer
        const lines = buffer.split('\n')
        buffer = lines.pop() || '' // Keep incomplete line in buffer

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))

              switch (data.type) {
                case 'text':
                  accumulatedText += data.content
                  setMessages(prev => {
                    const updated = [...prev]
                    updated[updated.length - 1] = {
                      role: 'assistant',
                      content: accumulatedText,
                      streaming: true,
                    }
                    return updated
                  })
                  break

                case 'tool_call':
                  setToolActivity(prev => [
                    ...prev,
                    { tool: data.tool, status: 'running' }
                  ])
                  break

                case 'tool_result':
                  setToolActivity(prev =>
                    prev.map(t =>
                      t.tool === data.tool && t.status === 'running'
                        ? { ...t, status: data.success ? 'done' : 'error' }
                        : t
                    )
                  )
                  break

                case 'done':
                  setMessages(prev => {
                    const updated = [...prev]
                    updated[updated.length - 1] = {
                      role: 'assistant',
                      content: accumulatedText,
                      streaming: false,
                    }
                    return updated
                  })

                  // Update conversation history for multi-turn
                  conversationHistory.current.push(
                    { role: 'user', content: userMessage },
                    { role: 'assistant', content: [{ type: 'text', text: accumulatedText }] }
                  )
                  break

                case 'error':
                  console.error('Agent error:', data.message)
                  break
              }
            } catch (e) {
              // Skip non-JSON lines (SSE comments, etc.)
            }
          }
        }
      }
    } catch (error) {
      console.error('Stream error:', error)
      setMessages(prev => {
        const updated = [...prev]
        updated[updated.length - 1] = {
          role: 'assistant',
          content: `Connection error: ${error.message}. Make sure the backend is running on port 8000.`,
          streaming: false,
        }
        return updated
      })
    }

    setIsLoading(false)
    setToolActivity([])
    inputRef.current?.focus()
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage(input)
    }
  }

  const toolLabel = (name) => {
    const labels = {
      get_soil_moisture: 'Checking soil moisture',
      get_disease_risk: 'Checking disease risk',
      get_weather_forecast: 'Fetching weather forecast',
      get_canopy_environment: 'Reading canopy sensors',
      get_farm_overview: 'Scanning all blocks',
    }
    return labels[name] || `Running ${name}`
  }

  return (
    <div className="chat-container">
      <div className="chat-messages">
        {messages.length === 0 && (
          <div className="welcome">
            <h2>Naramata Hills AI Assistant</h2>
            <p>
              Ask about soil moisture, disease risk, irrigation needs,
              weather conditions, or sensor status across your vineyard blocks.
            </p>
            <div className="example-queries">
              {EXAMPLE_QUERIES.map((q, i) => (
                <button
                  key={i}
                  className="example-query"
                  onClick={() => sendMessage(q)}
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`message message-${msg.role}`}>
            {msg.role === 'assistant' ? (
              <ReactMarkdown>{msg.content || '...'}</ReactMarkdown>
            ) : (
              msg.content
            )}
          </div>
        ))}

        {/* Tool activity indicators */}
        {toolActivity.map((tool, i) => (
          <div key={i} className={`tool-indicator ${tool.status}`}>
            <span className="dot" />
            {tool.status === 'running'
              ? `${toolLabel(tool.tool)}...`
              : tool.status === 'done'
              ? `${toolLabel(tool.tool)} ✓`
              : `${toolLabel(tool.tool)} failed`}
          </div>
        ))}

        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input-area">
        <div className="chat-input-wrapper">
          <input
            ref={inputRef}
            type="text"
            className="chat-input"
            placeholder="Ask about your vineyard..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
          />
          <button
            className="chat-send"
            onClick={() => sendMessage(input)}
            disabled={isLoading || !input.trim()}
          >
            {isLoading ? 'Thinking...' : 'Send'}
          </button>
        </div>
      </div>
    </div>
  )
}
