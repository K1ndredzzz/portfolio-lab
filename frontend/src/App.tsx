import React from 'react';
import PortfolioBuilder from './components/PortfolioBuilder';
import RiskDashboard from './components/RiskDashboard';
import MonteCarloChart from './components/MonteCarloChart';
import StressTestChart from './components/StressTestChart';

const App: React.FC = () => {
  return (
    <div className="app">
      <header className="app-header">
        <h1>📊 Portfolio Lab</h1>
        <p>Investment Portfolio Risk Analysis Platform</p>
      </header>

      <main className="app-main">
        <div className="section">
          <PortfolioBuilder />
        </div>

        <div className="section">
          <RiskDashboard />
        </div>

        <div className="section">
          <MonteCarloChart />
        </div>

        <div className="section">
          <StressTestChart />
        </div>
      </main>

      <footer className="app-footer">
        <p>Portfolio Lab v1.0.0 | Powered by FastAPI + React</p>
      </footer>

      <style>{`
        * {
          box-sizing: border-box;
          margin: 0;
          padding: 0;
        }

        body {
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
            'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue',
            sans-serif;
          -webkit-font-smoothing: antialiased;
          -moz-osx-font-smoothing: grayscale;
          background: #f5f5f5;
        }

        .app {
          min-height: 100vh;
          display: flex;
          flex-direction: column;
        }

        .app-header {
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          color: white;
          padding: 40px 20px;
          text-align: center;
          box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }

        .app-header h1 {
          font-size: 48px;
          margin-bottom: 10px;
        }

        .app-header p {
          font-size: 18px;
          opacity: 0.9;
        }

        .app-main {
          flex: 1;
          max-width: 1400px;
          width: 100%;
          margin: 0 auto;
          padding: 40px 20px;
        }

        .section {
          margin-bottom: 40px;
        }

        .app-footer {
          background: #333;
          color: white;
          text-align: center;
          padding: 20px;
          font-size: 14px;
        }

        /* Loading spinner */
        .spinner {
          display: inline-block;
          width: 40px;
          height: 40px;
          border: 4px solid #f3f3f3;
          border-top: 4px solid #007bff;
          border-radius: 50%;
          animation: spin 1s linear infinite;
        }

        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }

        /* Focus visible for accessibility */
        :focus-visible {
          outline: 2px solid #007bff;
          outline-offset: 2px;
        }

        /* Responsive */
        @media (max-width: 768px) {
          .app-header h1 {
            font-size: 32px;
          }

          .app-header p {
            font-size: 14px;
          }

          .app-main {
            padding: 20px 10px;
          }
        }
      `}</style>
    </div>
  );
};

export default App;
