import { resume } from '../clients/tradingClient';

export async function run() {
  const r = await resume();
  console.log('[resume]', r);
}
