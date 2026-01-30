import { positions } from '../clients/tradingClient';

export async function run() {
  const p = await positions();
  console.log('[positions]', JSON.stringify(p));
}
