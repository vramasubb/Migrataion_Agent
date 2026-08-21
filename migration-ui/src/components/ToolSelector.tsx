import React from 'react';
import type { MigrationToolOption } from '../types';

interface Props {
  tools: MigrationToolOption[];
  selected: string;
  onChange: (id: string) => void;
}

const ToolSelector: React.FC<Props> = ({ tools, selected, onChange }) => {
  return (
    <div className="tool-selector">
      <h2 className="section-title">Select Migration Type</h2>
      <div className="tool-grid">
        {tools.map((tool) => (
          <button
            key={tool.id}
            className={`tool-card ${selected === tool.id ? 'selected' : ''}`}
            onClick={() => onChange(tool.id)}
            type="button"
          >
            <span className="tool-icon">{tool.icon}</span>
            <span className="tool-label">{tool.label}</span>
            <span className="tool-source">{tool.sourceLabel}</span>
            <span className="tool-desc">{tool.description}</span>
          </button>
        ))}
      </div>
    </div>
  );
};

export default ToolSelector;
