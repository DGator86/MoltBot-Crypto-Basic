import { flatten } from '../clients/tradingClient';

export async function run() {
  const r = await flatten();
  console.log('[flatten]', r);
}
