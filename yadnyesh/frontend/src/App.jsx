import React, { useState } from 'react';
import './App.css';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:3001';

function App() {
  const [isRegister, setIsRegister] = useState(false);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [status, setStatus]     = useState(null); // null | 'loading' | 'success' | 'error'
  const [errorMsg, setErrorMsg] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setStatus('loading');

    if (isRegister && password !== confirmPassword) {
      setErrorMsg('Passwords do not match.');
      setStatus('error');
      return;
    }

    const endpoint = isRegister ? '/api/register' : '/api/login';

    try {
      const res = await fetch(`${API_URL}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });

      const data = await res.json().catch(() => ({}));

      if (res.ok) {
        setStatus('success');
        if (isRegister) {
          // Auto switch to login mode after successful registration
          setTimeout(() => {
            setIsRegister(false);
            setPassword('');
            setConfirmPassword('');
            setStatus(null);
          }, 2000);
        }
      } else {
        setErrorMsg(data.message || (isRegister ? 'Registration failed.' : 'Invalid credentials. Access denied.'));
        setStatus('error');
      }
    } catch (err) {
      setErrorMsg('Cannot reach server. Is the backend running on port 3001?');
      setStatus('error');
    }
  };

  return (
    <div className="app-container">
      {/* Animated background orbs */}
      <div className="shape shape-1"></div>
      <div className="shape shape-2"></div>
      <div className="shape shape-3"></div>

      <div className="login-wrapper">
        <div className="login-box">
          <div className="login-header">
            <div className="logo-icon">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M12 2L2 7L12 12L22 7L12 2Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                <path d="M2 17L12 22L22 17" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                <path d="M2 12L12 17L22 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </div>
            <h2>Smart SOC</h2>
            <p className="subtitle">Secure Command Center</p>
          </div>

          {/* Alert Banner */}
          <div className={`alert-container ${status ? 'visible' : ''}`}>
            {status === 'success' && (
              <div className="alert success">
                <span className="alert-icon">✓</span>
                {isRegister ? 'Registration successful! Proceed to login.' : 'Authentication successful. Redirecting...'}
              </div>
            )}
            {status === 'error' && (
              <div className="alert error">
                <span className="alert-icon">✕</span>
                {errorMsg}
              </div>
            )}
          </div>

          <form onSubmit={handleSubmit} className={status === 'success' && !isRegister ? 'fade-out' : ''}>
            <div className="input-group">
              <input
                type="text"
                id="username"
                value={username}
                onChange={(e) => { setUsername(e.target.value); if (status === 'error') setStatus(null); }}
                required
                autoComplete="off"
              />
              <label htmlFor="username">Operator ID</label>
              <div className="input-highlight"></div>
            </div>

            <div className="input-group">
              <input
                type="password"
                id="password"
                value={password}
                onChange={(e) => { setPassword(e.target.value); if (status === 'error') setStatus(null); }}
                required
              />
              <label htmlFor="password">Security Clearance Code</label>
              <div className="input-highlight"></div>
            </div>

            {isRegister && (
              <div className="input-group">
                <input
                  type="password"
                  id="confirmPassword"
                  value={confirmPassword}
                  onChange={(e) => { setConfirmPassword(e.target.value); if (status === 'error') setStatus(null); }}
                  required
                />
                <label htmlFor="confirmPassword">Confirm Clearance Code</label>
                <div className="input-highlight"></div>
              </div>
            )}

            <button
              type="submit"
              id="login-btn"
              disabled={status === 'loading' || (status === 'success' && !isRegister)}
              className={`submit-btn ${status === 'loading' ? 'loading' : ''}`}
            >
              <span className="btn-text">{isRegister ? 'Register Identity' : 'Initialize Link'}</span>
              <div className="btn-loader"></div>
            </button>
          </form>

          <div className="footer-links" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '10px' }}>
            <div>
              <a href="#" onClick={(e) => {
                e.preventDefault();
                setIsRegister(!isRegister);
                setStatus(null);
                setErrorMsg('');
              }}>
                {isRegister ? 'Already have clearance? Initialize Link' : "Don't have clearance? Register"}
              </a>
            </div>
            {!isRegister && (
              <div>
                <a href="#">Forgot Clearance?</a>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
