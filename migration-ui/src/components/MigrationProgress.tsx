import React, { useEffect, useRef } from 'react';
import type { LogEntry, MigrationStatus } from '../types';

interface Props {
  status: MigrationStatus;
  currentStage: string;
  logs: LogEntry[];
  onStop: () => void;
  onReset: () => void;
}

const STAGE_ORDER = ['Analyzing source', 'Generating user stories', 'Gate 1 review', 'Implementing Playwright', 'Running tests', 'Gate 2 review', 'Complete'];

const MigrationProgress: React.FC<Props> = ({ status, currentStage, logs, onStop, onReset }) => {
  const logEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  const stageIndex = STAGE_ORDER.findIndex((s) => currentStage.toLowerCase().includes(s.toLowerCase().split(' ')[0]));

  return (
    <div className="migration-progress">
      {/* Status banner */}
      <div className={`status-banner status-${status}`}>
        <span className="status-dot" />
        <span className="status-text">
          {status === 'running' && `Running — ${currentStage}`}
          {status === 'completed' && '✅ Migration completed successfully'}
          {status === 'failed' && '❌ Migration failed'}
          {status === 'idle' && 'Ready'}
        </span>
        <div className="status-actions">
          {status === 'running' && (
            <button className="btn-danger-sm" onClick={onStop}>⏹ Stop</button>
          )}
          {(status === 'completed' || status === 'failed') && (
            <button className="btn-secondary-sm" onClick={onReset}>↩ New Migration</button>
          )}
        </div>
      </div>

      {/* Stage pipeline */}
      <div className="stage-pipeline">
        {STAGE_ORDER.map((stage, i) => (
          <div
            key={stage}
            className={`stage-step ${i < stageIndex ? 'done' : i === stageIndex ? 'active' : 'pending'}`}
          >
            <div className="stage-dot">{i < stageIndex ? '✓' : i + 1}</div>
            <div className="stage-name">{stage}</div>
          </div>
        ))}
      </div>

      {/* Log console */}
      <div className="log-console">
        <div className="log-header">
          <span>Agent Output</span>
          <span className="log-count">{logs.length} lines</span>
        </div>
        <div className="log-body">
          {logs.length === 0 && (
            <div className="log-empty">Waiting for agent output…</div>
          )}
          {logs.map((entry, i) => (
            <div key={i} className={`log-line log-${entry.level}`}>
              <span className="log-time">{entry.timestamp}</span>
              <span className="log-msg">{entry.message}</span>
            </div>
          ))}
          <div ref={logEndRef} />
        </div>
      </div>
    </div>
  );
};

export default MigrationProgress;
