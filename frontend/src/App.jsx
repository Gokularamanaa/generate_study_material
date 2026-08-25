import React, { useState, useEffect } from 'react';
import './index.css';

export default function App() {
  const [courseInfo, setCourseInfo] = useState({
    subject_name: '',
    course_code: '',
    unit_number: 1,
    unit_title: ''
  });

  const [topics, setTopics] = useState([
    { id: 1, topic_name: '', duration: 2 }
  ]);

  const [backendStatus, setBackendStatus] = useState({
    connected: false,
    text: 'Checking Backend...'
  });

  const [isGenerating, setIsGenerating] = useState(false);
  const [generationResult, setGenerationResult] = useState(null);
  const [generationError, setGenerationError] = useState(null);

  // Check backend health on mount
  useEffect(() => {
    async function checkHealth() {
      try {
        const res = await fetch('/api/status');
        if (res.ok) {
          setBackendStatus({ connected: true, text: 'Connected (http://localhost:8000)' });
        } else {
          setBackendStatus({ connected: false, text: `Backend Warning (HTTP ${res.status})` });
        }
      } catch (err) {
        setBackendStatus({ connected: false, text: 'Backend Disconnected' });
      }
    }
    checkHealth();
  }, []);

  const handleCourseChange = (e) => {
    const { name, value } = e.target;
    setCourseInfo(prev => ({
      ...prev,
      [name]: name === 'unit_number' ? parseInt(value, 10) || 1 : value
    }));
  };

  const handleTopicChange = (id, field, value) => {
    setTopics(prev => prev.map(t => {
      if (t.id === id) {
        return {
          ...t,
          [field]: field === 'duration' ? parseInt(value, 10) || 1 : value
        };
      }
      return t;
    }));
  };

  const addTopic = () => {
    const newId = topics.length > 0 ? Math.max(...topics.map(t => t.id)) + 1 : 1;
    setTopics(prev => [...prev, { id: newId, topic_name: '', duration: 2 }]);
  };

  const removeTopic = (id) => {
    if (topics.length === 1) return;
    setTopics(prev => prev.filter(t => t.id !== id));
  };

  const loadSampleData = () => {
    setCourseInfo({
      subject_name: 'Computer Networks',
      course_code: 'CS3591',
      unit_number: 2,
      unit_title: 'Transport Layer'
    });
    setTopics([
      { id: 1, topic_name: 'TCP', duration: 2 },
      { id: 2, topic_name: 'UDP', duration: 1 }
    ]);
  };

  const handleGenerate = async () => {
    if (!courseInfo.subject_name.trim() || !courseInfo.course_code.trim() || !courseInfo.unit_title.trim()) {
      alert('Please complete all Course Information fields.');
      return;
    }

    const validTopics = topics.filter(t => t.topic_name.trim() !== '');
    if (validTopics.length === 0) {
      alert('Please provide at least one valid Topic Name.');
      return;
    }

    const payload = {
      subject_name: courseInfo.subject_name.trim(),
      course_code: courseInfo.course_code.trim(),
      unit_number: courseInfo.unit_number,
      unit_title: courseInfo.unit_title.trim(),
      topics: validTopics.map(t => ({
        topic_name: t.topic_name.trim(),
        duration: t.duration
      }))
    };

    setIsGenerating(true);
    setGenerationResult(null);
    setGenerationError(null);

    try {
      const response = await fetch('/generate-study-material', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const data = await response.json();
      setIsGenerating(false);

      if (response.ok && data.success) {
        setGenerationResult(data);
      } else {
        setGenerationError(data.detail || data.reason || 'Generation failed.');
      }
    } catch (err) {
      setIsGenerating(false);
      setGenerationError(`Network Error: ${err.message}. Please verify FastAPI server at http://localhost:8000.`);
    }
  };

  const copyPath = (path) => {
    if (!path) return;
    navigator.clipboard.writeText(path);
    alert('Path copied to clipboard:\n' + path);
  };

  const getPdfUrl = (pdfPath) => {
    if (!pdfPath) return '#';
    const cleanPath = pdfPath.replace(/\\/g, '/');
    const parts = cleanPath.split('/output/');
    return parts.length > 1 ? `/output/${parts[1]}` : '#';
  };

  return (
    <div class="app-container">
      {/* Header */}
      <header className="app-header">
        <div className="brand">
          <div className="brand-icon">⚛️</div>
          <div className="brand-text">
            <h1>Academic Study Material AI</h1>
            <p>Dynamic React Frontend & PDF Compiler</p>
          </div>
        </div>
        <div className="status-pills">
          <div className="pill">
            <span className={`dot ${backendStatus.connected ? 'active' : ''}`}></span>
            <span>{backendStatus.text}</span>
          </div>
          <div className="pill">
            <span>Model: <strong style={{ color: 'var(--accent-cyan)' }}>OpenAI (gpt-4o)</strong></span>
          </div>
        </div>
      </header>

      {/* Main Content Layout */}
      <main className="main-grid">
        {/* Left Column: Form Controls */}
        <section className="form-section">
          {/* Course Metadata Card */}
          <div className="card">
            <div className="card-header">
              <h2><span>01</span> Course Information</h2>
              <button type="button" className="btn btn-secondary" onClick={loadSampleData}>
                ⚡ Load Sample Data
              </button>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label>Subject Name</label>
                <input
                  type="text"
                  name="subject_name"
                  className="form-control"
                  placeholder="e.g. Computer Networks"
                  value={courseInfo.subject_name}
                  onChange={handleCourseChange}
                />
              </div>
              <div className="form-group">
                <label>Course Code</label>
                <input
                  type="text"
                  name="course_code"
                  className="form-control"
                  placeholder="e.g. CS3591"
                  value={courseInfo.course_code}
                  onChange={handleCourseChange}
                />
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label>Unit Number</label>
                <input
                  type="number"
                  name="unit_number"
                  className="form-control"
                  min="1"
                  max="20"
                  value={courseInfo.unit_number}
                  onChange={handleCourseChange}
                />
              </div>
              <div className="form-group">
                <label>Unit Title</label>
                <input
                  type="text"
                  name="unit_title"
                  className="form-control"
                  placeholder="e.g. Transport Layer"
                  value={courseInfo.unit_title}
                  onChange={handleCourseChange}
                />
              </div>
            </div>
          </div>

          {/* Topics Card */}
          <div className="card">
            <div className="card-header">
              <h2><span>02</span> Topic Details</h2>
              <button type="button" className="btn btn-secondary" onClick={addTopic}>
                ＋ Add Topic
              </button>
            </div>

            {topics.map((t, index) => (
              <div key={t.id} className="topic-card">
                <div className="topic-header">
                  <span className="topic-title-badge">Topic #{index + 1}</span>
                  {topics.length > 1 && (
                    <button
                      type="button"
                      className="btn-remove-topic"
                      onClick={() => removeTopic(t.id)}
                    >
                      ✕ Remove
                    </button>
                  )}
                </div>
                <div className="form-row">
                  <div className="form-group" style={{ flex: 2 }}>
                    <label>Topic Name</label>
                    <input
                      type="text"
                      className="form-control"
                      placeholder="e.g. TCP Handshake & Congestion Control"
                      value={t.topic_name}
                      onChange={(e) => handleTopicChange(t.id, 'topic_name', e.target.value)}
                    />
                  </div>
                  <div className="form-group" style={{ flex: 1 }}>
                    <label>Duration (Hours)</label>
                    <input
                      type="number"
                      className="form-control"
                      min="1"
                      max="50"
                      value={t.duration}
                      onChange={(e) => handleTopicChange(t.id, 'duration', e.target.value)}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Action Button */}
          <button
            type="button"
            className="btn btn-primary btn-full"
            disabled={isGenerating}
            onClick={handleGenerate}
          >
            {isGenerating ? (
              <>
                <span className="spinner"></span>
                <span>Generating Study Material...</span>
              </>
            ) : (
              <span>🚀 Generate Study Material PDF</span>
            )}
          </button>
        </section>

        {/* Right Column: Generation Dashboard */}
        <section className="results-section">
          <div className="card progress-card">
            <div className="card-header">
              <h2><span>03</span> Generation Dashboard</h2>
              <span
                className="pill"
                style={{
                  color: isGenerating
                    ? 'var(--accent-cyan)'
                    : generationResult
                    ? 'var(--success)'
                    : generationError
                    ? 'var(--error)'
                    : 'var(--text-muted)'
                }}
              >
                {isGenerating ? 'Generating...' : generationResult ? 'Completed' : generationError ? 'Error' : 'Ready'}
              </span>
            </div>

            {/* Dashboard States */}
            {isGenerating && (
              <div className="result-banner" style={{ background: 'rgba(99, 102, 241, 0.15)', border: '1px solid rgba(99, 102, 241, 0.3)', color: 'var(--primary)' }}>
                <div className="spinner" style={{ width: '28px', height: '28px' }}></div>
                <div className="banner-text">
                  <h3>Generating Topic Content...</h3>
                  <p>Prompting OpenAI (gpt-4o) and compiling textbook PDF.</p>
                </div>
              </div>
            )}

            {generationError && (
              <div className="result-banner failed">
                <div className="banner-icon">⚠️</div>
                <div className="banner-text">
                  <h3>Generation Failed</h3>
                  <p>{generationError}</p>
                </div>
              </div>
            )}

            {generationResult && (
              <>
                <div className="result-banner success">
                  <div className="banner-icon">✅</div>
                  <div className="banner-text">
                    <h3>Study Material Generated!</h3>
                    <p>{generationResult.subject_name} ({generationResult.course_code}) - Unit {generationResult.unit_number}: {generationResult.unit_title}</p>
                  </div>
                </div>

                <div className="topic-result-list">
                  {generationResult.topic_results?.map((tr, idx) => (
                    <div key={idx} className={`topic-result-item ${tr.status === 'success' ? 'success' : 'failed'}`} style={{ flexDirection: 'column', alignItems: 'stretch', gap: '8px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div>
                          <strong style={{ fontSize: '1rem', color: 'var(--text-main)' }}>Topic {idx + 1}: {tr.topic_name}</strong>
                          {tr.reason && <div style={{ fontSize: '0.75rem', color: 'var(--error)', marginTop: '2px' }}>{tr.reason}</div>}
                        </div>
                        <span className={`status-badge ${tr.status === 'success' ? 'success' : 'failed'}`}>
                          {tr.status === 'success' ? '✓ PDF Ready' : '✗ Failed'}
                        </span>
                      </div>

                      {tr.status === 'success' && tr.pdf_path && (
                        <div className="pdf-action-row" style={{ marginTop: '4px', paddingTop: '8px', borderTop: '1px stroke var(--border-color, #e2e8f0)' }}>
                          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Path: <code>{tr.pdf_path}</code></span>
                          <div style={{ display: 'flex', gap: '8px', marginTop: '4px' }}>
                            <a
                              href={getPdfUrl(tr.pdf_path)}
                              target="_blank"
                              rel="noreferrer"
                              className="btn btn-primary btn-sm"
                              download
                            >
                              ⬇️ Download Topic PDF
                            </a>
                            <button
                              type="button"
                              className="btn btn-secondary btn-sm"
                              onClick={() => copyPath(tr.pdf_path)}
                            >
                              📋 Copy Path
                            </button>
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </>
            )}

            {!isGenerating && !generationResult && !generationError && (
              <div className="empty-state">
                <div className="empty-state-icon">📄</div>
                <p>Fill course details and topics on the left, then click <strong>Generate Study Material PDF</strong> to start AI generation.</p>
              </div>
            )}
          </div>
        </section>
      </main>
    </div>
  );
}
