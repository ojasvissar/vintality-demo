import React, { useState, useEffect } from 'react'
import { Line, Bar } from 'react-chartjs-2'
import {
  Chart as ChartJS, CategoryScale, LinearScale, PointElement,
  LineElement, BarElement, Filler, Tooltip, Legend
} from 'chart.js'

ChartJS.register(
  CategoryScale, LinearScale, PointElement, LineElement,
  BarElement, Filler, Tooltip, Legend
)

const STATUS_COLORS = {
  critical: { bg: '#fdf0ef', text: '#c0392b', border: '#e6a19a' },
  warning:  { bg: '#fef9ef', text: '#b07d10', border: '#f0dca0' },
  good:     { bg: '#eef6f1', text: '#2d6a4f', border: '#a8d5ba' },
}

function statusFromBlock(b) {
  if (b.avg_vwc && b.avg_vwc < 30) return 'critical'
  if (b.pm_risk_score && b.pm_risk_score > 60) return 'critical'
  if (b.avg_vwc && b.avg_vwc < 38) return 'warning'
  if (b.pm_risk_score && b.pm_risk_score > 40) return 'warning'
  if (b.deficit_mm && b.deficit_mm > 25) return 'warning'
  return 'good'
}

function statusLabel(s) {
  return s === 'critical' ? 'Needs attention' : s === 'warning' ? 'Monitor' : 'Healthy'
}

export default function Dashboard({ onAskAI }) {
  const [blocks, setBlocks] = useState([])
  const [weather, setWeather] = useState([])
  const [selectedBlock, setSelectedBlock] = useState(null)
  const [soilTrend, setSoilTrend] = useState([])
  const [diseaseTrend, setDiseaseTrend] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      fetch('/api/dashboard/blocks').then(r => r.json()),
      fetch('/api/dashboard/weather').then(r => r.json()),
    ]).then(([b, w]) => {
      setBlocks(b)
      setWeather(w)
      setLoading(false)
      if (b.length > 0) selectBlock(b[0].code)
    }).catch(() => setLoading(false))
  }, [])

  const selectBlock = (code) => {
    setSelectedBlock(code)
    fetch(`/api/dashboard/blocks/${code}/soil-trend`).then(r => r.json()).then(setSoilTrend)
    fetch(`/api/dashboard/blocks/${code}/disease-trend`).then(r => r.json()).then(setDiseaseTrend)
  }

  if (loading) return <div className="dash-loading">Loading farm data...</div>

  const currentBlock = blocks.find(b => b.code === selectedBlock)

  return (
    <div className="dashboard">
      {/* Block status cards */}
      <div className="dash-section">
        <div className="dash-header">
          <h2>Block overview</h2>
          <button className="ai-btn" onClick={() => onAskAI('Which blocks need attention most urgently?')}>
            Ask AI ↗
          </button>
        </div>
        <div className="block-cards">
          {blocks.map(b => {
            const st = statusFromBlock(b)
            const c = STATUS_COLORS[st]
            return (
              <div
                key={b.code}
                className={`block-card ${selectedBlock === b.code ? 'selected' : ''}`}
                onClick={() => selectBlock(b.code)}
              >
                <div className="block-card-top">
                  <span className="block-code">{b.code}</span>
                  <span className="block-status" style={{ background: c.bg, color: c.text, borderColor: c.border }}>
                    {statusLabel(st)}
                  </span>
                </div>
                <div className="block-varietal">{b.varietal}</div>
                <div className="block-metrics">
                  <div className="metric">
                    <span className="metric-label">VWC</span>
                    <span className="metric-value" style={{ color: b.avg_vwc < 30 ? '#c0392b' : b.avg_vwc < 38 ? '#b07d10' : '#2d6a4f' }}>
                      {b.avg_vwc ? `${b.avg_vwc}%` : '—'}
                    </span>
                  </div>
                  <div className="metric">
                    <span className="metric-label">Deficit</span>
                    <span className="metric-value">{b.deficit_mm ? `${Math.round(b.deficit_mm)}mm` : '—'}</span>
                  </div>
                  <div className="metric">
                    <span className="metric-label">PM risk</span>
                    <span className="metric-value" style={{ color: b.pm_risk_score > 60 ? '#c0392b' : b.pm_risk_score > 40 ? '#b07d10' : '#2d6a4f' }}>
                      {b.pm_risk_score ? Math.round(b.pm_risk_score) : '—'}
                    </span>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Detail charts for selected block */}
      {currentBlock && (
        <div className="dash-charts">
          <div className="chart-panel">
            <div className="chart-header">
              <h3>Soil moisture — {currentBlock.code} {currentBlock.varietal}</h3>
              <button className="ai-btn-sm" onClick={() => onAskAI(`What's the soil moisture trend for ${currentBlock.code} over the last week?`)}>
                Ask AI ↗
              </button>
            </div>
            <div className="chart-container">
              <SoilChart data={soilTrend} />
            </div>
          </div>
          <div className="chart-panel">
            <div className="chart-header">
              <h3>Disease risk — {currentBlock.code}</h3>
              <button className="ai-btn-sm" onClick={() => onAskAI(`Why is PM risk ${currentBlock.pm_risk_score > 60 ? 'high' : 'at this level'} on ${currentBlock.code}?`)}>
                Ask AI ↗
              </button>
            </div>
            <div className="chart-container">
              <DiseaseChart data={diseaseTrend} />
            </div>
          </div>
        </div>
      )}

      {/* Weather strip */}
      <div className="dash-section">
        <div className="dash-header">
          <h3>48h forecast</h3>
          <button className="ai-btn-sm" onClick={() => onAskAI('Is there a spray window in the next 24 hours?')}>
            Spray window? ↗
          </button>
        </div>
        <WeatherStrip data={weather} />
      </div>
    </div>
  )
}


function SoilChart({ data }) {
  if (!data.length) return <div className="chart-empty">Loading...</div>

  // Downsample to every 4th hour for readability
  const sampled = data.filter((_, i) => i % 4 === 0)
  const labels = sampled.map(d => {
    const dt = new Date(d.hour)
    return `${dt.getMonth()+1}/${dt.getDate()} ${dt.getHours()}:00`
  })

  return (
    <Line
      data={{
        labels,
        datasets: [{
          label: 'VWC %',
          data: sampled.map(d => d.vwc),
          borderColor: '#2d6a4f',
          backgroundColor: 'rgba(45,106,79,0.08)',
          fill: true,
          tension: 0.3,
          pointRadius: 0,
          borderWidth: 2,
        }]
      }}
      options={{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: { label: ctx => `VWC: ${ctx.parsed.y}%` }
          },
        },
        scales: {
          x: {
            ticks: { maxTicksLimit: 7, font: { size: 10 } },
            grid: { display: false },
          },
          y: {
            min: 20, max: 55,
            ticks: { callback: v => `${v}%`, font: { size: 10 } },
            grid: { color: 'rgba(0,0,0,0.04)' },
          },
        },
        // Draw threshold lines
        annotation: {},
      }}
      plugins={[{
        id: 'thresholds',
        beforeDraw(chart) {
          const { ctx } = chart
          const yAxis = chart.scales.y

          // Critical threshold at 30%
          const y30 = yAxis.getPixelForValue(30)
          ctx.save()
          ctx.strokeStyle = 'rgba(192,57,43,0.4)'
          ctx.setLineDash([4, 4])
          ctx.lineWidth = 1
          ctx.beginPath()
          ctx.moveTo(chart.chartArea.left, y30)
          ctx.lineTo(chart.chartArea.right, y30)
          ctx.stroke()

          // Field capacity at 45%
          const y45 = yAxis.getPixelForValue(45)
          ctx.strokeStyle = 'rgba(45,106,79,0.3)'
          ctx.beginPath()
          ctx.moveTo(chart.chartArea.left, y45)
          ctx.lineTo(chart.chartArea.right, y45)
          ctx.stroke()
          ctx.restore()

          // Labels
          ctx.fillStyle = 'rgba(192,57,43,0.6)'
          ctx.font = '10px Inter, sans-serif'
          ctx.fillText('Critical 30%', chart.chartArea.right - 65, y30 - 4)
          ctx.fillStyle = 'rgba(45,106,79,0.5)'
          ctx.fillText('Field cap 45%', chart.chartArea.right - 72, y45 - 4)
        }
      }]}
    />
  )
}


function DiseaseChart({ data }) {
  if (!data.length) return <div className="chart-empty">Loading...</div>

  const labels = data.map(d => {
    const dt = new Date(d.date + 'T00:00')
    return `${dt.getMonth()+1}/${dt.getDate()}`
  })

  return (
    <Bar
      data={{
        labels,
        datasets: [
          {
            label: 'PM risk',
            data: data.map(d => d.pm_risk),
            backgroundColor: data.map(d =>
              d.pm_risk > 60 ? 'rgba(192,57,43,0.7)' :
              d.pm_risk > 40 ? 'rgba(176,125,16,0.6)' :
              'rgba(45,106,79,0.5)'
            ),
            borderRadius: 3,
            barPercentage: 0.6,
          },
          {
            label: 'Botrytis',
            data: data.map(d => d.botrytis),
            backgroundColor: 'rgba(140,140,160,0.3)',
            borderRadius: 3,
            barPercentage: 0.6,
          },
        ]
      }}
      options={{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'bottom', labels: { font: { size: 11 }, boxWidth: 12 } },
        },
        scales: {
          x: { grid: { display: false }, ticks: { font: { size: 10 } } },
          y: {
            min: 0, max: 100,
            ticks: { font: { size: 10 } },
            grid: { color: 'rgba(0,0,0,0.04)' },
          },
        },
      }}
      plugins={[{
        id: 'sprayLine',
        beforeDraw(chart) {
          const { ctx } = chart
          const y60 = chart.scales.y.getPixelForValue(60)
          ctx.save()
          ctx.strokeStyle = 'rgba(192,57,43,0.4)'
          ctx.setLineDash([4, 4])
          ctx.lineWidth = 1
          ctx.beginPath()
          ctx.moveTo(chart.chartArea.left, y60)
          ctx.lineTo(chart.chartArea.right, y60)
          ctx.stroke()
          ctx.restore()
          ctx.fillStyle = 'rgba(192,57,43,0.6)'
          ctx.font = '10px Inter, sans-serif'
          ctx.fillText('Spray threshold', chart.chartArea.right - 78, y60 - 4)
        }
      }]}
    />
  )
}


function WeatherStrip({ data }) {
  if (!data.length) return null

  // Show every 3 hours
  const sampled = data.filter((_, i) => i % 3 === 0).slice(0, 12)

  return (
    <div className="weather-strip">
      {sampled.map((h, i) => {
        const dt = new Date(h.forecast_for)
        const isNight = dt.getHours() < 6 || dt.getHours() > 20
        return (
          <div key={i} className="weather-hour">
            <span className="wh-time">
              {dt.getHours() === 0 ? `${dt.getMonth()+1}/${dt.getDate()}` : `${dt.getHours()}:00`}
            </span>
            <span className="wh-temp" style={{ color: h.temp_c > 30 ? '#c0392b' : h.temp_c < 5 ? '#2d6a9f' : 'var(--text-primary)' }}>
              {Math.round(h.temp_c)}°
            </span>
            <span className="wh-detail">
              {Math.round(h.humidity_pct)}%
            </span>
            <span className="wh-detail">
              {Math.round(h.wind_speed_kmh)}km/h
            </span>
            <span className={`wh-rain ${h.rain_prob_pct > 30 ? 'rain-likely' : ''}`}>
              {Math.round(h.rain_prob_pct)}%
            </span>
            {h.frost_risk && <span className="wh-frost">FROST</span>}
          </div>
        )
      })}
    </div>
  )
}
