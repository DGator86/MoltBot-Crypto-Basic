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
/**
 * Moltbot Bridge CLI - Command-line interface for trading operations
 */
import { Command } from 'commander';
import MoltbotBridge from './bridge';
import * as dotenv from 'dotenv';

dotenv.config();

const program = new Command();
const bridge = new MoltbotBridge();

program
  .name('moltbot')
  .description('Moltbot crypto trading bridge CLI')
  .version('1.0.0');

program
  .command('status')
  .description('Get trading system status')
  .action(async () => {
    try {
      const status = await bridge.status();
      console.log('Trading System Status:');
      console.log('---------------------');
      console.log(`Paused: ${status.is_paused}`);
      console.log(`Kill Switch: ${status.kill_switch_active}`);
      console.log(`Positions: ${status.positions_count}`);
      console.log(`Max Position Size: ${status.risk_limits.max_position_size}`);
      console.log(`Max Total Exposure: ${status.risk_limits.max_total_exposure}`);
      console.log(`Timestamp: ${status.timestamp}`);
    } catch (error: any) {
      console.error('Error:', error.message);
      process.exit(1);
    }
  });

program
  .command('positions')
  .description('Get current positions')
  .action(async () => {
    try {
      const positions = await bridge.positions();
      console.log('Current Positions:');
      console.log('------------------');
      if (positions.length === 0) {
        console.log('No open positions');
      } else {
        positions.forEach((pos, idx) => {
          console.log(`\nPosition ${idx + 1}:`);
          console.log(`  Exchange: ${pos.exchange}`);
          console.log(`  Symbol: ${pos.symbol}`);
          console.log(`  Amount: ${pos.amount}`);
          console.log(`  Entry Price: ${pos.entry_price}`);
          console.log(`  Current Price: ${pos.current_price}`);
          console.log(`  Unrealized P&L: ${pos.unrealized_pnl}`);
        });
      }
    } catch (error: any) {
      console.error('Error:', error.message);
      process.exit(1);
    }
  });

program
  .command('pause')
  .description('Pause trading')
  .action(async () => {
    try {
      const result = await bridge.pause();
      console.log(`Trading paused at ${result.timestamp}`);
    } catch (error: any) {
      console.error('Error:', error.message);
      process.exit(1);
    }
  });

program
  .command('resume')
  .description('Resume trading')
  .action(async () => {
    try {
      const result = await bridge.resume();
      console.log(`Trading resumed at ${result.timestamp}`);
    } catch (error: any) {
      console.error('Error:', error.message);
      process.exit(1);
    }
  });

program
  .command('flatten')
  .description('Close all positions')
  .action(async () => {
    try {
      const result = await bridge.flatten();
      console.log('Flattening all positions...');
      console.log(JSON.stringify(result, null, 2));
    } catch (error: any) {
      console.error('Error:', error.message);
      process.exit(1);
    }
  });

program
  .command('propose')
  .description('Propose a trade for approval')
  .requiredOption('-e, --exchange <exchange>', 'Exchange (binance|coinbase)')
  .requiredOption('-s, --symbol <symbol>', 'Trading symbol (e.g., BTC/USDT)')
  .requiredOption('-d, --side <side>', 'Order side (buy|sell)')
  .requiredOption('-t, --type <type>', 'Order type (market|limit)')
  .requiredOption('-a, --amount <amount>', 'Order amount')
  .option('-p, --price <price>', 'Order price (for limit orders)')
  .action(async (options) => {
    try {
      const order = {
        exchange: options.exchange as 'binance' | 'coinbase',
        symbol: options.symbol,
        side: options.side as 'buy' | 'sell',
        type: options.type as 'market' | 'limit',
        amount: parseFloat(options.amount),
        price: options.price ? parseFloat(options.price) : undefined,
      };

      const proposal = await bridge.propose(order);
      console.log('Trade Proposal:');
      console.log('---------------');
      console.log(`Proposal ID: ${proposal.proposal_id}`);
      console.log(`Risk Check: ${proposal.risk_check.passed ? 'PASSED' : 'FAILED'}`);
      if (proposal.risk_check.reason) {
        console.log(`Reason: ${proposal.risk_check.reason}`);
      }
      console.log(`\nOrder Details:`);
      console.log(JSON.stringify(proposal.order, null, 2));
    } catch (error: any) {
      console.error('Error:', error.message);
      process.exit(1);
    }
  });

program
  .command('approve')
  .description('Approve and execute a proposed trade')
  .requiredOption('-i, --id <proposalId>', 'Proposal ID')
  .requiredOption('-e, --exchange <exchange>', 'Exchange (binance|coinbase)')
  .requiredOption('-s, --symbol <symbol>', 'Trading symbol (e.g., BTC/USDT)')
  .requiredOption('-d, --side <side>', 'Order side (buy|sell)')
  .requiredOption('-t, --type <type>', 'Order type (market|limit)')
  .requiredOption('-a, --amount <amount>', 'Order amount')
  .option('-p, --price <price>', 'Order price (for limit orders)')
  .action(async (options) => {
    try {
      const order = {
        exchange: options.exchange as 'binance' | 'coinbase',
        symbol: options.symbol,
        side: options.side as 'buy' | 'sell',
        type: options.type as 'market' | 'limit',
        amount: parseFloat(options.amount),
        price: options.price ? parseFloat(options.price) : undefined,
      };

      const result = await bridge.approve(options.id, order);
      console.log('Order Executed:');
      console.log('---------------');
      console.log(`Order ID: ${result.order_id}`);
      console.log(`Status: ${result.status}`);
      console.log(JSON.stringify(result, null, 2));
    } catch (error: any) {
      console.error('Error:', error.message);
      process.exit(1);
    }
  });

program
  .command('health')
  .description('Check system health')
  .action(async () => {
    try {
      const health = await bridge.health();
      console.log('System Health:');
      console.log('--------------');
      console.log(JSON.stringify(health, null, 2));
    } catch (error: any) {
      console.error('Error:', error.message);
      process.exit(1);
    }
  });

program.parse(process.argv);
