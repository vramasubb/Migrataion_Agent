import React from 'react';
import type { MigrationConfig, MigrationToolOption, MigrationStrategy } from '../types';

interface Props {
  config: MigrationConfig;
  selectedTool: MigrationToolOption | undefined;
  onChange: (updates: Partial<MigrationConfig>) => void;
  onSubmit: () => void;
  disabled: boolean;
}

const STRATEGIES: Array<{
  id: MigrationStrategy;
  icon: string;
  name: string;
  flow: string;
  features: string[];
  badge: string;
  badgeClass: string;
  hint: string;
}> = [
  {
    id: 'reverse-engineering',
    icon: '🔍',
    name: 'Reverse Engineering',
    flow: 'Selenium  →  User Stories  →  Playwright',
    features: [
      '✅ Analysis docs per feature',
      '✅ Business user stories generated',
      '✅ Gate 1: stakeholder review',
      '✅ Gate 2: final review',
    ],
    badge: 'Full Documentation',
    badgeClass: 'badge-re',
    hint: 'Best when: business sign-off is required before coding',
  },
  {
    id: 'direct',
    icon: '⚡',
    name: 'Direct Migration',
    flow: 'Selenium  →  Playwright',
    features: [
      '❌ No analysis docs',
      '❌ No user stories',
      '⏩ Single review gate',
      '⚡ Fastest path to running tests',
    ],
    badge: 'Code Only',
    badgeClass: 'badge-dm',
    hint: 'Best when: technical team, speed is the priority',
  },
];

const MigrationForm: React.FC<Props> = ({ config, selectedTool, onChange, onSubmit, disabled }) => {
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit();
  };

  return (
    <form className="migration-form" onSubmit={handleSubmit}>
      <h2 className="section-title">Configure Migration</h2>

      {/* ── Strategy Selector (Selenium tools only) ── */}
      {selectedTool?.supportsStrategies && (
        <div className="form-group">
          <label>Migration Strategy</label>
          <div className="strategy-cards">
            {STRATEGIES.map((s) => (
              <button
                key={s.id}
                type="button"
                className={`strategy-card${config.strategy === s.id ? ' selected' : ''}`}
                onClick={() => onChange({ strategy: s.id })}
                disabled={disabled}
              >
                <div className="strategy-header">
                  <span className="strategy-icon">{s.icon}</span>
                  <span className="strategy-name">{s.name}</span>
                  <span className={`strategy-badge ${s.badgeClass}`}>{s.badge}</span>
                </div>
                <code className="strategy-flow">{s.flow}</code>
                <ul className="strategy-features">
                  {s.features.map((f) => <li key={f}>{f}</li>)}
                </ul>
                <p className="strategy-hint">{s.hint}</p>
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="form-group">
        <label htmlFor="projectName">Project Name</label>
        <input
          id="projectName"
          type="text"
          value={config.projectName}
          onChange={(e) => onChange({ projectName: e.target.value })}
          placeholder="my-automation-project"
          required
          disabled={disabled}
        />
      </div>

      <div className="form-group">
        <label htmlFor="sourcePath">
          Source Folder Path
          {selectedTool && (
            <span className="label-hint"> — {selectedTool.sourceLabel} project root</span>
          )}
        </label>
        <input
          id="sourcePath"
          type="text"
          value={config.sourcePath}
          onChange={(e) => onChange({ sourcePath: e.target.value })}
          placeholder="C:\projects\my-selenium-tests"
          required
          disabled={disabled}
        />
        <p className="field-hint">Full path to the root of your existing test project</p>
      </div>

      <div className="form-group">
        <label htmlFor="outputPath">Output Folder Path</label>
        <input
          id="outputPath"
          type="text"
          value={config.outputPath}
          onChange={(e) => onChange({ outputPath: e.target.value })}
          placeholder={
            config.strategy === 'direct'
              ? 'C:\\projects\\sawslab-playwright-dm'
              : 'C:\\projects\\sawslab-playwright-re'
          }
          required
          disabled={disabled}
        />
        <p className="field-hint">
          {config.strategy === 'direct'
            ? 'Direct migration output — Playwright project only, no analysis docs'
            : 'Reverse engineering output — includes analysis docs, user stories, and Playwright project'}
        </p>
      </div>

      {selectedTool && selectedTool.sourceLanguages.length > 1 && (
        <div className="form-group">
          <label htmlFor="sourceLanguage">Source Language</label>
          <select
            id="sourceLanguage"
            value={config.sourceLanguage}
            onChange={(e) => onChange({ sourceLanguage: e.target.value })}
            disabled={disabled}
          >
            {selectedTool.sourceLanguages.map((lang) => (
              <option key={lang} value={lang}>{lang}</option>
            ))}
          </select>
        </div>
      )}

      <div className="form-row">
        <div className="form-group">
          <label htmlFor="webTarget">Web Target URL <span className="optional">(optional)</span></label>
          <input
            id="webTarget"
            type="url"
            value={config.webTarget ?? ''}
            onChange={(e) => onChange({ webTarget: e.target.value })}
            placeholder="https://app.example.com"
            disabled={disabled}
          />
        </div>

        <div className="form-group">
          <label htmlFor="apiTarget">API Base URL <span className="optional">(optional)</span></label>
          <input
            id="apiTarget"
            type="url"
            value={config.apiTarget ?? ''}
            onChange={(e) => onChange({ apiTarget: e.target.value })}
            placeholder="https://api.example.com"
            disabled={disabled}
          />
        </div>
      </div>

      <button
        type="submit"
        className="btn-primary"
        disabled={disabled || !config.sourcePath || !config.outputPath || !config.projectName}
      >
        {disabled
          ? 'Migration Running…'
          : config.strategy === 'direct'
          ? '⚡ Start Direct Migration'
          : '🔍 Start Reverse Engineering Migration'}
      </button>
    </form>
  );
};

export default MigrationForm;

