import React from 'react';
import type { MigrationConfig, MigrationState, MigrationToolOption } from '../types';
import { MIGRATION_TOOLS } from '../services/migrationTools';
import { api } from '../services/api';
import ToolSelector from '../components/ToolSelector';
import MigrationForm from '../components/MigrationForm';
import MigrationProgress from '../components/MigrationProgress';

const DEFAULT_CONFIG: MigrationConfig = {
  tool: 'selenium-playwright',
  strategy: 'reverse-engineering',
  sourcePath: '',
  outputPath: '',
  projectName: '',
  sourceLanguage: 'Java',
};

const DEFAULT_STATE: MigrationState = {
  status: 'idle',
  currentStage: '',
  logs: [],
};

const HomePage: React.FC = () => {
  const [config, setConfig] = React.useState<MigrationConfig>(DEFAULT_CONFIG);
  const [migState, setMigState] = React.useState<MigrationState>(DEFAULT_STATE);
  const esRef = React.useRef<EventSource | null>(null);

  const selectedTool: MigrationToolOption | undefined = MIGRATION_TOOLS.find((t) => t.id === config.tool);

  const handleToolChange = (id: string) => {
    const tool = MIGRATION_TOOLS.find((t) => t.id === id);
    setConfig((c) => ({
      ...c,
      tool: id as MigrationConfig['tool'],
      sourceLanguage: tool?.sourceLanguages[0] ?? 'Java',
    }));
  };

  const handleConfigChange = (updates: Partial<MigrationConfig>) => {
    setConfig((c) => ({ ...c, ...updates }));
  };

  const handleStart = async () => {
    try {
      await api.startMigration(config);
    } catch (err: any) {
      setMigState((s) => ({
        ...s,
        status: 'failed',
        error: err?.response?.data?.error ?? err.message,
        logs: [...s.logs, { timestamp: now(), level: 'error', message: `Failed to start: ${err.message}` }],
      }));
      return;
    }

    setMigState({ status: 'running', currentStage: 'Analyzing source', logs: [] });

    esRef.current = api.streamLogs(
      (entry) => setMigState((s) => ({
        ...s,
        currentStage: entry.message.startsWith('STAGE:') ? entry.message.replace('STAGE:', '').trim() : s.currentStage,
        logs: [...s.logs, entry],
      })),
      () => setMigState((s) => ({ ...s, status: 'completed', currentStage: 'Complete' })),
      (errMsg) => setMigState((s) => ({ ...s, status: 'failed', error: errMsg,
        logs: [...s.logs, { timestamp: now(), level: 'error', message: errMsg }],
      })),
    );
  };

  const handleStop = async () => {
    esRef.current?.close();
    await api.stopMigration().catch(() => {});
    setMigState((s) => ({ ...s, status: 'failed', currentStage: 'Stopped',
      logs: [...s.logs, { timestamp: now(), level: 'warn', message: 'Migration stopped by user.' }],
    }));
  };

  const handleReset = () => {
    esRef.current?.close();
    setMigState(DEFAULT_STATE);
  };

  const isRunning = migState.status === 'running';
  const showProgress = migState.status !== 'idle';

  return (
    <div className="home-page">
      <header className="app-header">
        <div className="header-brand">
          <span className="brand-icon">⚡</span>
          <div>
            <h1>Test Migration Agent</h1>
            <p>AI-powered migration from legacy automation frameworks to Playwright</p>
          </div>
        </div>
      </header>

      <main className="app-main">
        {!showProgress ? (
          <div className="setup-panel">
            <ToolSelector tools={MIGRATION_TOOLS} selected={config.tool} onChange={handleToolChange} />
            <MigrationForm
              config={config}
              selectedTool={selectedTool}
              onChange={handleConfigChange}
              onSubmit={handleStart}
              disabled={isRunning}
            />
          </div>
        ) : (
          <div className="progress-panel">
            {migState.status === 'idle' || (!isRunning && migState.status !== 'completed' && migState.status !== 'failed') ? null : (
              <MigrationProgress
                status={migState.status}
                currentStage={migState.currentStage}
                logs={migState.logs}
                onStop={handleStop}
                onReset={handleReset}
              />
            )}
            {(migState.status === 'completed' || migState.status === 'failed') && (
              <div className="action-bar">
                <button className="btn-secondary" onClick={handleReset}>← Configure New Migration</button>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
};

function now() {
  return new Date().toLocaleTimeString();
}

export default HomePage;
