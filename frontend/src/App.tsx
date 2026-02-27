import React from 'react';
import PortfolioBuilder from './components/PortfolioBuilder';
import RiskDashboard from './components/RiskDashboard';
import MonteCarloChart from './components/MonteCarloChart';
import StressTestChart from './components/StressTestChart';

const App: React.FC = () => {
  return (
    <div className="app dark-theme">
      <header className="app-header">
        <div className="header-content">
          <div className="logo">
            <h1>📊 Portfolio Lab</h1>
            <p className="subtitle">Investment Portfolio Risk Analysis Platform</p>
          </div>
          <div className="header-actions">
            <a 
              href="https://github.com/K1ndredzzz/portfolio-lab" 
              target="_blank" 
              rel="noopener noreferrer"
              className="github-link"
            >
              <svg height="24" aria-hidden="true" viewBox="0 0 16 16" version="1.1" width="24" fill="currentColor">
                <path d="M8 0c4.42 0 8 3.58 8 8a8.013 8.013 0 0 1-5.45 7.59c-.4.08-.55-.17-.55-.38 0-.27.01-1.13.01-2.2 0-.75-.25-1.23-.54-1.48 1.78-.2 3.65-.88 3.65-3.95 0-.88-.31-1.59-.82-2.15.08-.2.36-1.02-.08-2.12 0 0-.67-.22-2.2.82-.64-.18-1.32-.27-2-.27-.68 0-1.36.09-2 .27-1.53-1.03-2.2-.82-2.2-.82-.44 1.1-.16 1.92-.08 2.12-.51.56-.82 1.28-.82 2.15 0 3.06 1.86 3.75 3.64 3.95-.23.2-.44.55-.51 1.07-.46.21-1.61.55-2.33-.66-.15-.24-.6-.83-1.23-.82-.67.01-.27.38.01.53.34.19.73.9.82 1.13.16.45.68 1.31 2.69.94 0 .67.01 1.3.01 1.49 0 .21-.15.45-.55.38A7.995 7.995 0 0 1 0 8c0-4.42 3.58-8 8-8Z"></path>
              </svg>
              GitHub
            </a>
          </div>
        </div>
      </header>

      <main className="app-main">
        <div className="dashboard-grid">
          <div className="builder-section">
            <PortfolioBuilder />
          </div>
          <div className="risk-section">
            <RiskDashboard />
          </div>
        </div>

        <div className="charts-grid">
          <div className="chart-section">
            <MonteCarloChart />
          </div>
          <div className="chart-section">
            <StressTestChart />
          </div>
        </div>
      </main>

      <footer className="app-footer">
        <p>Portfolio Lab v1.0.0 | Powered by FastAPI + React | Designed for Quantitative Finance</p>
      </footer>

      <style>{`
        * {
          box-sizing: border-box;
          margin: 0;
          padding: 0;
        }

        :root {
          --bg-dark: #0B0F19;
          --bg-panel: #111827;
          --bg-panel-hover: #1F2937;
          --text-primary: #F3F4F6;
          --text-secondary: #9CA3AF;
          --accent-green: #10B981;
          --accent-green-hover: #059669;
          --accent-blue: #3B82F6;
          --border-color: #374151;
          --danger: #EF4444;
          --warning: #F59E0B;
        }

        body {
          font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
            'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue',
            sans-serif;
          -webkit-font-smoothing: antialiased;
          -moz-osx-font-smoothing: grayscale;
          background: var(--bg-dark);
          color: var(--text-primary);
        }

        .app {
          min-height: 100vh;
          display: flex;
          flex-direction: column;
        }

        .app-header {
          background: var(--bg-panel);
          border-bottom: 1px solid var(--border-color);
          padding: 24px 40px;
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5);
        }

        .header-content {
          max-width: 1600px;
          margin: 0 auto;
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .logo h1 {
          font-size: 32px;
          font-weight: 700;
          letter-spacing: -0.5px;
          margin-bottom: 4px;
          background: linear-gradient(90deg, #F3F4F6 0%, #9CA3AF 100%);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
        }

        .subtitle {
          font-size: 14px;
          color: var(--accent-green);
          font-weight: 500;
          letter-spacing: 0.5px;
          text-transform: uppercase;
        }

        .github-link {
          display: flex;
          align-items: center;
          gap: 8px;
          color: var(--text-secondary);
          text-decoration: none;
          font-weight: 600;
          font-size: 14px;
          padding: 8px 16px;
          border-radius: 6px;
          border: 1px solid var(--border-color);
          transition: all 0.2s ease;
          background: rgba(255, 255, 255, 0.03);
        }

        .github-link:hover {
          color: var(--text-primary);
          border-color: var(--text-secondary);
          background: rgba(255, 255, 255, 0.08);
        }

        .app-main {
          flex: 1;
          max-width: 1600px;
          width: 100%;
          margin: 0 auto;
          padding: 32px;
          display: flex;
          flex-direction: column;
          gap: 32px;
        }

        .dashboard-grid {
          display: grid;
          grid-template-columns: 1fr 1.5fr;
          gap: 32px;
        }

        .charts-grid {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 32px;
        }

        .builder-section,
        .risk-section,
        .chart-section {
          background: var(--bg-panel);
          border: 1px solid var(--border-color);
          border-radius: 12px;
          box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
          overflow: hidden;
        }

        .app-footer {
          background: var(--bg-panel);
          color: var(--text-secondary);
          text-align: center;
          padding: 24px;
          font-size: 13px;
          border-top: 1px solid var(--border-color);
          letter-spacing: 0.5px;
        }

        /* Loading spinner container */
        .spinner {
          display: inline-block;
          width: 40px;
          height: 40px;
          border: 3px solid rgba(255, 255, 255, 0.1);
          border-top: 3px solid var(--accent-green);
          border-radius: 50%;
          animation: spin 1s linear infinite;
        }

        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }

        /* Focus visible for accessibility */
        :focus-visible {
          outline: 2px solid var(--accent-green);
          outline-offset: 2px;
        }

        /* Responsive */
        @media (max-width: 1200px) {
          .charts-grid {
            grid-template-columns: 1fr;
          }
        }

        @media (max-width: 1024px) {
          .dashboard-grid {
            grid-template-columns: 1fr;
          }
          .header-content {
            flex-direction: column;
            gap: 16px;
            align-items: flex-start;
          }
        }
      `}</style>
    </div>
  );
};

export default App;
