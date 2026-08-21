import axios from 'axios';
import type { MigrationConfig } from '../types';
import type { LogEntry } from '../types';

const BASE_URL = '/api';  // proxied to http://localhost:3001 by Vite

export const api = {
  startMigration: (config: MigrationConfig) =>
    axios.post(`${BASE_URL}/migrate`, config),

  stopMigration: () =>
    axios.post(`${BASE_URL}/migrate/stop`),

  getStatus: () =>
    axios.get(`${BASE_URL}/migrate/status`),

  streamLogs: (onLog: (entry: LogEntry) => void, onDone: () => void, onError: (err: string) => void): EventSource => {
    const es = new EventSource(`${BASE_URL}/migrate/stream`);

    es.addEventListener('log', (e) => {
      try {
        const entry: LogEntry = JSON.parse((e as MessageEvent).data);
        onLog(entry);
      } catch (err) {
        onError(`Failed to parse log event: ${(err as Error).message}`);
      }
    });

    es.addEventListener('done', () => {
      es.close();
      onDone();
    });

    es.addEventListener('error_event', (e) => {
      es.close();
      const raw = (e as MessageEvent).data;
      if (!raw) {
        onError('Migration failed');
        return;
      }

      try {
        const parsed = JSON.parse(raw);
        onError(parsed.message ?? raw);
      } catch {
        onError(raw);
      }
    });

    return es;
  },
};
