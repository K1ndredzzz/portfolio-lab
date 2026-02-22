CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE SCHEMA IF NOT EXISTS portfolio_lab;
SET search_path TO portfolio_lab, public;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'model_type') THEN
        CREATE TYPE model_type AS ENUM (
            'markowitz',
            'black_litterman',
            'risk_parity',
            'min_variance',
            'max_sharpe'
        );
    END IF;
END$$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'artifact_format') THEN
        CREATE TYPE artifact_format AS ENUM ('parquet', 'npz', 'json', 'csv');
    END IF;
END$$;

CREATE TABLE IF NOT EXISTS dataset_versions (
    dataset_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version_tag TEXT NOT NULL UNIQUE,
    date_start DATE NOT NULL,
    date_end DATE NOT NULL,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_active BOOLEAN NOT NULL DEFAULT FALSE,
    notes TEXT,
    CHECK (date_start <= date_end)
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_dataset_active_true
ON dataset_versions (is_active)
WHERE is_active = TRUE;

CREATE TABLE IF NOT EXISTS assets (
    asset_id SMALLSERIAL PRIMARY KEY,
    ticker TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    asset_class TEXT NOT NULL,
    currency TEXT NOT NULL DEFAULT 'USD',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS portfolios (
    portfolio_id BIGSERIAL PRIMARY KEY,
    universe_hash CHAR(64) NOT NULL,
    weights_hash CHAR(64) NOT NULL,
    weights_vector DOUBLE PRECISION[] NOT NULL,
    weights_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (array_length(weights_vector, 1) = 11),
    UNIQUE (universe_hash, weights_hash)
);

CREATE INDEX IF NOT EXISTS idx_portfolios_weights_hash
ON portfolios (weights_hash);

CREATE TABLE IF NOT EXISTS portfolio_metrics (
    metric_id BIGSERIAL PRIMARY KEY,
    dataset_id UUID NOT NULL REFERENCES dataset_versions(dataset_id) ON DELETE CASCADE,
    portfolio_id BIGINT NOT NULL REFERENCES portfolios(portfolio_id) ON DELETE CASCADE,
    model model_type NOT NULL,
    as_of_date DATE NOT NULL,
    horizon_months SMALLINT NOT NULL CHECK (horizon_months IN (12, 36, 60)),
    expected_return_ann DOUBLE PRECISION NOT NULL,
    volatility_ann DOUBLE PRECISION NOT NULL CHECK (volatility_ann >= 0),
    sharpe DOUBLE PRECISION NOT NULL,
    sortino DOUBLE PRECISION NOT NULL,
    var95 DOUBLE PRECISION NOT NULL,
    var99 DOUBLE PRECISION NOT NULL,
    cvar95 DOUBLE PRECISION NOT NULL,
    cvar99 DOUBLE PRECISION NOT NULL,
    max_drawdown DOUBLE PRECISION NOT NULL,
    calmar DOUBLE PRECISION NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (dataset_id, portfolio_id, model, as_of_date, horizon_months)
);

CREATE INDEX IF NOT EXISTS idx_portfolio_metrics_lookup
ON portfolio_metrics (dataset_id, model, as_of_date, horizon_months, portfolio_id);

CREATE TABLE IF NOT EXISTS frontier_points (
    frontier_id BIGSERIAL PRIMARY KEY,
    dataset_id UUID NOT NULL REFERENCES dataset_versions(dataset_id) ON DELETE CASCADE,
    model model_type NOT NULL,
    as_of_date DATE NOT NULL,
    horizon_months SMALLINT NOT NULL CHECK (horizon_months IN (12, 36, 60)),
    point_order INTEGER NOT NULL,
    portfolio_id BIGINT NOT NULL REFERENCES portfolios(portfolio_id) ON DELETE CASCADE,
    risk DOUBLE PRECISION NOT NULL CHECK (risk >= 0),
    expected_return DOUBLE PRECISION NOT NULL,
    sharpe DOUBLE PRECISION NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (dataset_id, model, as_of_date, horizon_months, point_order)
);

CREATE INDEX IF NOT EXISTS idx_frontier_lookup
ON frontier_points (dataset_id, model, as_of_date, horizon_months, point_order);

CREATE TABLE IF NOT EXISTS covariance_snapshots (
    cov_id BIGSERIAL PRIMARY KEY,
    dataset_id UUID NOT NULL REFERENCES dataset_versions(dataset_id) ON DELETE CASCADE,
    as_of_month DATE NOT NULL,
    window_days INTEGER NOT NULL DEFAULT 1260 CHECK (window_days > 0),
    asset_order TEXT[] NOT NULL,
    cov_matrix DOUBLE PRECISION[] NOT NULL,
    condition_number DOUBLE PRECISION,
    is_psd BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (dataset_id, as_of_month, window_days)
);

CREATE INDEX IF NOT EXISTS idx_covariance_lookup
ON covariance_snapshots (dataset_id, as_of_month, window_days);

CREATE TABLE IF NOT EXISTS stress_scenarios (
    scenario_id SMALLSERIAL PRIMARY KEY,
    scenario_code TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (period_start <= period_end)
);

CREATE TABLE IF NOT EXISTS stress_results (
    stress_result_id BIGSERIAL PRIMARY KEY,
    dataset_id UUID NOT NULL REFERENCES dataset_versions(dataset_id) ON DELETE CASCADE,
    scenario_id SMALLINT NOT NULL REFERENCES stress_scenarios(scenario_id),
    portfolio_id BIGINT NOT NULL REFERENCES portfolios(portfolio_id) ON DELETE CASCADE,
    as_of_date DATE NOT NULL,
    horizon_months SMALLINT NOT NULL CHECK (horizon_months IN (12, 36, 60)),
    total_return DOUBLE PRECISION NOT NULL,
    max_drawdown DOUBLE PRECISION NOT NULL,
    recovery_days INTEGER NOT NULL CHECK (recovery_days >= 0),
    path_summary JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (dataset_id, scenario_id, portfolio_id, as_of_date, horizon_months)
);

CREATE INDEX IF NOT EXISTS idx_stress_results_lookup
ON stress_results (dataset_id, scenario_id, as_of_date, horizon_months, portfolio_id);

CREATE TABLE IF NOT EXISTS monte_carlo_distributions (
    mc_id BIGSERIAL PRIMARY KEY,
    dataset_id UUID NOT NULL REFERENCES dataset_versions(dataset_id) ON DELETE CASCADE,
    portfolio_id BIGINT NOT NULL REFERENCES portfolios(portfolio_id) ON DELETE CASCADE,
    model model_type NOT NULL,
    as_of_date DATE NOT NULL,
    horizon_months SMALLINT NOT NULL CHECK (horizon_months IN (12, 36, 60)),
    n_paths INTEGER NOT NULL CHECK (n_paths > 0),
    seed INTEGER NOT NULL,
    q01 DOUBLE PRECISION NOT NULL,
    q05 DOUBLE PRECISION NOT NULL,
    q10 DOUBLE PRECISION NOT NULL,
    q25 DOUBLE PRECISION NOT NULL,
    q50 DOUBLE PRECISION NOT NULL,
    q75 DOUBLE PRECISION NOT NULL,
    q90 DOUBLE PRECISION NOT NULL,
    q95 DOUBLE PRECISION NOT NULL,
    q99 DOUBLE PRECISION NOT NULL,
    prob_loss DOUBLE PRECISION NOT NULL CHECK (prob_loss >= 0 AND prob_loss <= 1),
    prob_target_return DOUBLE PRECISION,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (dataset_id, portfolio_id, model, as_of_date, horizon_months)
);

CREATE INDEX IF NOT EXISTS idx_mc_lookup
ON monte_carlo_distributions (dataset_id, model, as_of_date, horizon_months, portfolio_id);

CREATE TABLE IF NOT EXISTS artifacts (
    artifact_id BIGSERIAL PRIMARY KEY,
    dataset_id UUID NOT NULL REFERENCES dataset_versions(dataset_id) ON DELETE CASCADE,
    artifact_name TEXT NOT NULL,
    format artifact_format NOT NULL,
    uri TEXT NOT NULL,
    file_size_bytes BIGINT NOT NULL CHECK (file_size_bytes >= 0),
    sha256 CHAR(64) NOT NULL,
    row_count BIGINT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (dataset_id, artifact_name)
);

CREATE INDEX IF NOT EXISTS idx_artifacts_dataset
ON artifacts (dataset_id, format);

INSERT INTO assets (ticker, display_name, asset_class, currency)
VALUES
    ('SPY', 'SPDR S&P 500 ETF Trust', 'Equity_US', 'USD'),
    ('QQQ', 'Invesco QQQ Trust', 'Equity_US', 'USD'),
    ('IWM', 'iShares Russell 2000 ETF', 'Equity_US_SmallCap', 'USD'),
    ('TLT', 'iShares 20+ Year Treasury Bond ETF', 'Rates_US', 'USD'),
    ('GLD', 'SPDR Gold Shares', 'Commodity_Gold', 'USD'),
    ('BTC', 'Bitcoin Spot Proxy', 'Crypto', 'USD'),
    ('EEM', 'iShares MSCI Emerging Markets ETF', 'Equity_EM', 'USD'),
    ('EFA', 'iShares MSCI EAFE ETF', 'Equity_DM_exUS', 'USD'),
    ('FXI', 'iShares China Large-Cap ETF', 'Equity_China', 'USD'),
    ('USO', 'United States Oil Fund', 'Commodity_Oil', 'USD'),
    ('DBA', 'Invesco DB Agriculture Fund', 'Commodity_Agriculture', 'USD')
ON CONFLICT (ticker) DO NOTHING;

INSERT INTO stress_scenarios (scenario_code, display_name, period_start, period_end, description)
VALUES
    ('crisis_2008', 'Global Financial Crisis 2008', '2008-09-01', '2009-03-31', 'Severe equity selloff and credit stress'),
    ('covid_2020', 'COVID Shock 2020', '2020-02-15', '2020-05-31', 'Fast drawdown and volatility spike with sharp rebound'),
    ('rate_hike_2022', 'Rate Hike Regime 2022', '2022-01-01', '2022-12-31', 'Synchronous drawdown in equities and long-duration bonds')
ON CONFLICT (scenario_code) DO NOTHING;
