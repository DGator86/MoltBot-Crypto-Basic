import { health } from '../clients/tradingClient';

export async function run() {
  const h = await health();
  console.log('[status] trading_core health:', h);
}
