# 📊 Portfolio Lab

A high-performance quantitative financial analysis platform built with a FastAPI backend, PostgreSQL database, and a React + Vite frontend. It features advanced portfolio optimization, risk analysis, stress testing, and Monte Carlo simulations.

[![Docker](https://img.shields.io/badge/Docker-Ready-blue)](https://hub.docker.com/u/fuzhouxing)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-green)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18.2-blue)](https://react.dev/)

---

## ✨ Features

- **Portfolio Optimization**: Risk Parity, Max Sharpe, Min Variance models.
- **Risk Metrics**: VaR, CVaR, Max Drawdown, Sharpe, Sortino ratios.
- **Monte Carlo Simulations**: Visualizing return distributions across 10,000+ paths.
- **Stress Testing**: Pre-calculated historical crisis scenarios (2008 Crash, COVID, 2022 Rate Hikes).
- **Dark Mode Dashboard**: A sleek, high-end quantitative finance interface constructed with React and Plotly.js.

## 🚀 Quick Start

### Docker (Recommended)

The easiest way to run the entire application stack is via Docker Compose. The frontend images are hosted on Dockerhub under `fuzhouxing/portfolio-lab-frontend`.

```bash
# Clone the repository
git clone https://github.com/K1ndredzzz/portfolio-lab.git
cd portfolio-lab

# Start all services
docker-compose up -d
```

- **Frontend Application**: [http://localhost:8032](http://localhost:8032)
- **API Documentation**: [http://localhost:8030/api/v1/docs](http://localhost:8030/api/v1/docs)

### Local Development

**Backend API:**
```bash
pip install -r requirements.txt
docker-compose up -d postgres redis
uvicorn app.main:app --reload --port 8030
```

**Frontend React App:**
```bash
cd frontend
npm install
npm run dev
```

---

## 🏗️ Architecture

- **Backend**: Python (FastAPI), Pandas, PyPortfolioOpt, SciPy.
- **Frontend**: React, Typescript, Vite, Zustand, Plotly.js.
- **Database / Cache**: PostgreSQL, Redis.
- **Computation**: Pre-calculated data pipelines run on GCP for sub-500ms API response times.

---

## 👨‍💻 Author

**K1ndredzzz**
- GitHub: [https://github.com/K1ndredzzz](https://github.com/K1ndredzzz)
- Frontend Docker Images: [fuzhouxing/portfolio-lab-frontend](https://hub.docker.com/r/fuzhouxing/portfolio-lab-frontend)
