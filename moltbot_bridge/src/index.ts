import { run as status } from './commands/status';
import { run as positions } from './commands/positions';
import { run as pause } from './commands/pause';
import { run as resume } from './commands/resume';
import { run as flatten } from './commands/flatten';

async function main() {
  const cmd = process.argv[2] || 'status';
  const map: Record<string, () => Promise<void>> = { status, positions, pause, resume, flatten };
  if (!map[cmd]) {
    console.error('unknown command:', cmd);
    process.exit(1);
  }
  await map[cmd]();
}

main();
