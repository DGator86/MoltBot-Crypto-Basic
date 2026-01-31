/**
 * Moltbot Bridge - TypeScript client for interacting with Trading Core API
 */
import axios, { AxiosInstance } from 'axios';

export interface TradingStatus {
  is_paused: boolean;
  kill_switch_active: boolean;
  positions_count: number;
  risk_limits: {
    max_position_size: string;
    max_total_exposure: string;
    max_leverage: string;
  };
  timestamp: string;
}

export interface Position {
  exchange: string;
  symbol: string;
  amount: number;
  entry_price: number;
  current_price: number;
  unrealized_pnl: number;
}

export interface OrderRequest {
  exchange: 'binance' | 'coinbase';
  symbol: string;
  side: 'buy' | 'sell';
  type: 'market' | 'limit';
  amount: number;
  price?: number;
}

export interface OrderResponse {
  order_id: string;
  exchange: string;
  symbol: string;
  side: string;
  amount: number;
  price?: number;
  status: string;
  timestamp: string;
}

export interface ProposalResponse {
  proposal_id: string;
  order: OrderRequest;
  risk_check: {
    passed: boolean;
    reason?: string;
  };
  timestamp: string;
}

export class MoltbotBridge {
  private client: AxiosInstance;
  private baseUrl: string;

  constructor(baseUrl?: string) {
    this.baseUrl = baseUrl || process.env.TRADING_CORE_URL || 'http://localhost:8000';
    this.client = axios.create({
      baseURL: this.baseUrl,
      timeout: 10000,
      headers: {
        'Content-Type': 'application/json',
      },
    });
  }

  /**
   * Get trading system status
   */
  async status(): Promise<TradingStatus> {
    const response = await this.client.get<TradingStatus>('/status');
    return response.data;
  }

  /**
   * Get current positions
   */
  async positions(): Promise<Position[]> {
    const response = await this.client.get<Position[]>('/positions');
    return response.data;
  }

  /**
   * Pause trading
   */
  async pause(): Promise<{ status: string; timestamp: string }> {
    const response = await this.client.post('/pause');
    return response.data;
  }

  /**
   * Resume trading
   */
  async resume(): Promise<{ status: string; timestamp: string }> {
    const response = await this.client.post('/resume');
    return response.data;
  }

  /**
   * Flatten all positions (close all)
   */
  async flatten(): Promise<any> {
    const response = await this.client.post('/flatten');
    return response.data;
  }

  /**
   * Activate kill switch
   */
  async killSwitch(): Promise<any> {
    const response = await this.client.post('/kill-switch');
    return response.data;
  }

  /**
   * Deactivate kill switch
   */
  async deactivateKillSwitch(): Promise<any> {
    const response = await this.client.post('/kill-switch/deactivate');
    return response.data;
  }

  /**
   * Propose a trade for approval
   */
  async propose(order: OrderRequest): Promise<ProposalResponse> {
    const response = await this.client.post<ProposalResponse>('/propose', order);
    return response.data;
  }

  /**
   * Approve and execute a proposed trade
   */
  async approve(proposalId: string, order: OrderRequest): Promise<OrderResponse> {
    const response = await this.client.post<OrderResponse>(`/approve/${proposalId}`, order);
    return response.data;
  }

  /**
   * Place an order directly
   */
  async placeOrder(order: OrderRequest): Promise<OrderResponse> {
    const response = await this.client.post<OrderResponse>('/orders', order);
    return response.data;
  }

  /**
   * Get health status
   */
  async health(): Promise<any> {
    const response = await this.client.get('/health');
    return response.data;
  }
}

export default MoltbotBridge;
