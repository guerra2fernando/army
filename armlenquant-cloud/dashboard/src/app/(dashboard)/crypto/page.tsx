"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { CryptoSignal, CryptoCoin } from "@/types/api";
import {
  TrendingUp,
  TrendingDown,
  Minus,
  RefreshCw,
  Zap,
  BarChart3,
  Newspaper,
  Target,
  ArrowUpRight,
  ArrowDownRight,
  Loader2,
  AlertCircle,
  DollarSign,
  Activity,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";

export default function CryptoPage() {
  const queryClient = useQueryClient();
  const [analyzeSymbol, setAnalyzeSymbol] = useState("");

  const { data: market, isLoading: marketLoading, error: marketError } = useQuery({
    queryKey: ["crypto-market"],
    queryFn: () => api.getCryptoMarket(),
    refetchInterval: 60000, // Refresh every minute
  });

  const { data: signals, isLoading: signalsLoading } = useQuery({
    queryKey: ["crypto-signals"],
    queryFn: () => api.getCryptoSignals(),
    refetchInterval: 60000,
  });

  const { data: brief } = useQuery({
    queryKey: ["crypto-brief"],
    queryFn: () => api.getCryptoBrief(),
    retry: false,
  });

  const generateBriefMutation = useMutation({
    mutationFn: () => api.generateCryptoBrief(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["crypto-brief"] });
    },
  });

  const analyzeMutation = useMutation({
    mutationFn: (symbol: string) => api.analyzeCrypto(symbol),
  });

  const handleAnalyze = () => {
    if (analyzeSymbol.trim()) {
      analyzeMutation.mutate(analyzeSymbol.toUpperCase());
    }
  };

  const formatCurrency = (value: number) => {
    if (!value || typeof value !== 'number') return '$0';
    if (value >= 1e12) return `$${(value / 1e12).toFixed(2)}T`;
    if (value >= 1e9) return `$${(value / 1e9).toFixed(2)}B`;
    if (value >= 1e6) return `$${(value / 1e6).toFixed(2)}M`;
    return `$${value.toLocaleString()}`;
  };

  const formatPercent = (value: number) => {
    const formatted = value?.toFixed(2) || "0.00";
    return value >= 0 ? `+${formatted}%` : `${formatted}%`;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">Crypto Sentinel</h1>
          <p className="text-zinc-400">Market analysis and trading signals</p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={() => {
              queryClient.invalidateQueries({ queryKey: ["crypto-market"] });
              queryClient.invalidateQueries({ queryKey: ["crypto-signals"] });
            }}
            className="border-zinc-700 text-zinc-300 hover:bg-zinc-800 hover:text-white"
          >
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </Button>
          <Button
            onClick={() => generateBriefMutation.mutate()}
            disabled={generateBriefMutation.isPending}
            className="bg-emerald-500 hover:bg-emerald-600 text-black font-semibold"
          >
            {generateBriefMutation.isPending ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <Zap className="w-4 h-4 mr-2" />
            )}
            Generate Brief
          </Button>
        </div>
      </div>

      {/* Error State */}
      {marketError && (
        <Card className="bg-red-500/10 border-red-500/20">
          <CardContent className="p-4 flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-red-500" />
            <p className="text-red-400">
              Failed to load market data. The Crypto Sentinel may not be running.
            </p>
          </CardContent>
        </Card>
      )}

      {/* Global Stats */}
      {market?.global && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <GlobalStatCard
            title="Total Market Cap"
            value={formatCurrency(market.global.total_market_cap)}
            change={market.global.market_cap_change_24h}
            icon={DollarSign}
          />
          <GlobalStatCard
            title="24h Volume"
            value={formatCurrency(market.global.total_volume_24h)}
            icon={Activity}
          />
          <GlobalStatCard
            title="BTC Dominance"
            value={`${market.global.btc_dominance?.toFixed(1) || "0"}%`}
            icon={BarChart3}
          />
          <GlobalStatCard
            title="Active Cryptocurrencies"
            value={market.global.active_cryptocurrencies?.toLocaleString() || "0"}
            icon={Target}
          />
        </div>
      )}

      {/* Brief Summary */}
      {brief && (
        <Card className="bg-gradient-to-r from-emerald-500/10 via-emerald-500/5 to-transparent border-emerald-500/20">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-white">
              <Newspaper className="w-5 h-5 text-emerald-500" />
              Today&apos;s Brief
              <Badge
                variant="outline"
                className={
                  brief.market_sentiment === "BULLISH"
                    ? "bg-emerald-500/10 text-emerald-500 border-emerald-500/20"
                    : brief.market_sentiment === "BEARISH"
                    ? "bg-red-500/10 text-red-500 border-red-500/20"
                    : "bg-zinc-500/10 text-zinc-500 border-zinc-500/20"
                }
              >
                {brief.market_sentiment}
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-zinc-300 mb-4">{brief.summary}</p>
            {brief.top_movers && brief.top_movers.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {brief.top_movers.map((mover, i) => (
                  <Badge key={i} variant="outline" className="border-zinc-700 text-zinc-300">
                    {mover.coin}: {formatPercent(mover.change)}
                  </Badge>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Active Signals */}
        <Card className="lg:col-span-1 bg-zinc-900/50 border-zinc-800">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-white">
              <Target className="w-5 h-5 text-emerald-500" />
              Active Signals
            </CardTitle>
          </CardHeader>
          <CardContent>
            {signalsLoading ? (
              <div className="flex justify-center py-8">
                <Loader2 className="w-8 h-8 animate-spin text-zinc-500" />
              </div>
            ) : signals?.signals && signals.signals.length > 0 ? (
              <div className="space-y-3">
                {signals.signals.map((signal) => (
                  <SignalCard key={signal.signal_id} signal={signal} />
                ))}
              </div>
            ) : (
              <p className="text-zinc-500 text-center py-8">
                No active signals
              </p>
            )}
          </CardContent>
        </Card>

        {/* Top Coins */}
        <Card className="lg:col-span-2 bg-zinc-900/50 border-zinc-800">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-white">
              <TrendingUp className="w-5 h-5 text-emerald-500" />
              Top Coins
            </CardTitle>
          </CardHeader>
          <CardContent>
            {marketLoading ? (
              <div className="flex justify-center py-8">
                <Loader2 className="w-8 h-8 animate-spin text-zinc-500" />
              </div>
            ) : market?.top_coins && market.top_coins.length > 0 ? (
              <div className="space-y-2">
                {market.top_coins.slice(0, 10).map((coin, index) => (
                  <CoinRow key={coin.id || `coin-${index}`} coin={coin} />
                ))}
              </div>
            ) : (
              <p className="text-zinc-500 text-center py-8">
                No market data available
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Analyze Asset */}
      <Card className="bg-zinc-900/50 border-zinc-800">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-white">
            <BarChart3 className="w-5 h-5 text-emerald-500" />
            Analyze Asset
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-4 mb-6">
            <Input
              placeholder="Enter symbol (e.g., BTC, ETH, SOL)"
              value={analyzeSymbol}
              onChange={(e) => setAnalyzeSymbol(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleAnalyze()}
              className="flex-1 bg-zinc-800 border-zinc-700 text-white placeholder:text-zinc-500"
            />
            <Button
              onClick={handleAnalyze}
              disabled={analyzeMutation.isPending || !analyzeSymbol.trim()}
              className="bg-emerald-500 hover:bg-emerald-600 text-black font-semibold"
            >
              {analyzeMutation.isPending ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                "Analyze"
              )}
            </Button>
          </div>

          {analyzeMutation.data && (
            <div className="p-4 rounded-lg bg-zinc-800/50 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-xl font-bold text-white">
                  {analyzeMutation.data.symbol}
                </h3>
                <Badge
                  variant="outline"
                  className={
                    analyzeMutation.data.sentiment === "BULLISH"
                      ? "bg-emerald-500/10 text-emerald-500 border-emerald-500/20"
                      : analyzeMutation.data.sentiment === "BEARISH"
                      ? "bg-red-500/10 text-red-500 border-red-500/20"
                      : "bg-zinc-500/10 text-zinc-500 border-zinc-500/20"
                  }
                >
                  {analyzeMutation.data.sentiment}
                </Badge>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div>
                  <p className="text-sm text-zinc-500">Price</p>
                  <p className="text-lg font-semibold text-white">
                    ${analyzeMutation.data.price?.toLocaleString()}
                  </p>
                </div>
                {analyzeMutation.data.indicators && (
                  <>
                    <div>
                      <p className="text-sm text-zinc-500">RSI</p>
                      <p className={`text-lg font-semibold ${
                        analyzeMutation.data.indicators.rsi > 70 ? "text-red-500" :
                        analyzeMutation.data.indicators.rsi < 30 ? "text-emerald-500" :
                        "text-white"
                      }`}>
                        {analyzeMutation.data.indicators.rsi?.toFixed(1)}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-zinc-500">SMA 20</p>
                      <p className="text-lg font-semibold text-white">
                        ${analyzeMutation.data.indicators.sma_20?.toFixed(2)}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-zinc-500">SMA 50</p>
                      <p className="text-lg font-semibold text-white">
                        ${analyzeMutation.data.indicators.sma_50?.toFixed(2)}
                      </p>
                    </div>
                  </>
                )}
              </div>

              {analyzeMutation.data.summary && (
                <p className="text-zinc-300">{analyzeMutation.data.summary}</p>
              )}

              {analyzeMutation.data.signal && (
                <div className="p-3 rounded-lg bg-zinc-900/50 border border-zinc-700">
                  <SignalCard signal={analyzeMutation.data.signal} />
                </div>
              )}
            </div>
          )}

          {analyzeMutation.error && (
            <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/20">
              <p className="text-red-400">
                Failed to analyze {analyzeSymbol}. Please check the symbol and try again.
              </p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function GlobalStatCard({
  title,
  value,
  change,
  icon: Icon,
}: {
  title: string;
  value: string;
  change?: number;
  icon: React.ElementType;
}) {
  return (
    <Card className="bg-zinc-900/50 border-zinc-800">
      <CardContent className="p-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-zinc-400">{title}</p>
            <p className="text-2xl font-bold text-white mt-1">{value}</p>
            {change !== undefined && (
              <p className={`text-sm mt-1 flex items-center gap-1 ${
                change >= 0 ? "text-emerald-500" : "text-red-500"
              }`}>
                {change >= 0 ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
                {Math.abs(change).toFixed(2)}%
              </p>
            )}
          </div>
          <div className="p-3 rounded-full bg-zinc-800 text-emerald-500">
            <Icon className="w-6 h-6" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function SignalCard({ signal }: { signal: CryptoSignal }) {
  const signalColors = {
    BUY: "bg-emerald-500/10 text-emerald-500 border-emerald-500/20",
    SELL: "bg-red-500/10 text-red-500 border-red-500/20",
    HOLD: "bg-amber-500/10 text-amber-500 border-amber-500/20",
  };

  const SignalIcon = signal.signal_type === "BUY" ? TrendingUp : 
                     signal.signal_type === "SELL" ? TrendingDown : Minus;

  return (
    <div className="p-3 rounded-lg bg-zinc-800/50 hover:bg-zinc-800 transition-colors">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <SignalIcon className={`w-4 h-4 ${
            signal.signal_type === "BUY" ? "text-emerald-500" :
            signal.signal_type === "SELL" ? "text-red-500" : "text-amber-500"
          }`} />
          <span className="font-semibold text-white">{signal.symbol}</span>
        </div>
        <Badge variant="outline" className={signalColors[signal.signal_type]}>
          {signal.signal_type}
        </Badge>
      </div>
      <div className="grid grid-cols-2 gap-2 text-sm">
        <div>
          <span className="text-zinc-500">Entry:</span>{" "}
          <span className="text-zinc-300">${signal.entry_price?.toLocaleString()}</span>
        </div>
        <div>
          <span className="text-zinc-500">Confidence:</span>{" "}
          <span className="text-zinc-300">{signal.confidence}%</span>
        </div>
        {signal.target_price && (
          <div>
            <span className="text-zinc-500">Target:</span>{" "}
            <span className="text-emerald-500">${signal.target_price?.toLocaleString()}</span>
          </div>
        )}
        {signal.stop_loss && (
          <div>
            <span className="text-zinc-500">Stop:</span>{" "}
            <span className="text-red-500">${signal.stop_loss?.toLocaleString()}</span>
          </div>
        )}
      </div>
      {signal.reasoning && (
        <p className="mt-2 text-xs text-zinc-500 line-clamp-2">
          {typeof signal.reasoning === 'string' 
            ? signal.reasoning 
            : JSON.stringify(signal.reasoning)}
        </p>
      )}
    </div>
  );
}

function CoinRow({ coin }: { coin: CryptoCoin }) {
  const change24h = coin.price_change_percentage_24h || 0;
  const isPositive = change24h >= 0;

  return (
    <div className="flex items-center justify-between p-3 rounded-lg bg-zinc-800/50 hover:bg-zinc-800 transition-colors">
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-full bg-zinc-700 flex items-center justify-center text-xs font-bold text-zinc-300">
          {coin.market_cap_rank}
        </div>
        <div>
          <p className="font-semibold text-white">{coin.symbol?.toUpperCase()}</p>
          <p className="text-sm text-zinc-500">{coin.name}</p>
        </div>
      </div>
      <div className="text-right">
        <p className="font-semibold text-white">
          ${coin.current_price?.toLocaleString(undefined, { maximumFractionDigits: 2 })}
        </p>
        <p className={`text-sm flex items-center justify-end gap-1 ${
          isPositive ? "text-emerald-500" : "text-red-500"
        }`}>
          {isPositive ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
          {Math.abs(change24h).toFixed(2)}%
        </p>
      </div>
    </div>
  );
}

