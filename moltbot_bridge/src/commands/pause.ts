import { pause } from '../clients/tradingClient';

export async function run() {
  const r = await pause();
  console.log('[pause]', r);
}
