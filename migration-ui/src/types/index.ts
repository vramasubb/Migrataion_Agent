export type MigrationTool =
  | 'selenium-playwright'
  | 'robot-playwright'
  | 'uft-playwright'
  | 'cypress-playwright'
  | 'selenium-api-playwright';

/** re = full docs + user stories + 2 gates; direct = code only + 1 gate */
export type MigrationStrategy = 'reverse-engineering' | 'direct';

export interface MigrationToolOption {
  id: MigrationTool;
  label: string;
  sourceLabel: string;
  targetLabel: string;
  description: string;
  sourceLanguages: string[];
  icon: string;
  /** true when this tool has both RE and Direct migration paths */
  supportsStrategies?: boolean;
}

export interface MigrationConfig {
  tool: MigrationTool;
  strategy: MigrationStrategy;
  sourcePath: string;
  outputPath: string;
  projectName: string;
  sourceLanguage: string;
  webTarget?: string;
  apiTarget?: string;
}

export type MigrationStatus = 'idle' | 'running' | 'completed' | 'failed';

export interface LogEntry {
  timestamp: string;
  level: 'info' | 'warn' | 'error' | 'success';
  message: string;
}

export interface MigrationState {
  status: MigrationStatus;
  currentStage: string;
  logs: LogEntry[];
  outputPath?: string;
  error?: string;
}
