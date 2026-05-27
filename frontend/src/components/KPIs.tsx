import { Flame, ShieldCheck, AlertTriangle, Clock, TrendingUp } from 'lucide-react';
import type { DashboardStats } from '../types';

interface KPIsProps {
  stats: DashboardStats;
}

export default function KPIs({ stats }: KPIsProps) {
  return (
    <div className="stats-grid">
      <div className="stat-card carbon">
        <div className="stat-header">
          <span className="stat-title">Total CO2 Calculated</span>
          <Flame className="stat-icon" size={18} />
        </div>
        <div className="stat-value">
          {stats.total_co2e_kg.toLocaleString(undefined, { maximumFractionDigits: 1 })} kg
        </div>
        <div className="stat-footer">
          <TrendingUp size={14} className="trend-up" />
          <span>Calculated from {stats.total_records} rows</span>
        </div>
      </div>

      <div className="stat-card approved">
        <div className="stat-header">
          <span className="stat-title">Approved & Locked</span>
          <ShieldCheck className="stat-icon" size={18} />
        </div>
        <div className="stat-value">
          {stats.approved_co2e_kg.toLocaleString(undefined, { maximumFractionDigits: 1 })} kg
        </div>
        <div className="stat-footer">
          <span>{stats.approved_records_count} rows approved ({stats.approval_rate_pct}%)</span>
        </div>
      </div>

      <div className="stat-card flagged">
        <div className="stat-header">
          <span className="stat-title">Suspicious flagged</span>
          <AlertTriangle className="stat-icon" size={18} />
        </div>
        <div className="stat-value">{stats.flagged_records_count}</div>
        <div className="stat-footer">
          <span style={{ color: 'hsl(var(--status-flagged))' }}>
            {stats.flagged_rate_pct}% outlier flagging rate
          </span>
        </div>
      </div>

      <div className="stat-card progress-bar">
        <div className="stat-header">
          <span className="stat-title">Pending review</span>
          <Clock className="stat-icon" size={18} />
        </div>
        <div className="stat-value">
          {stats.pending_co2e_kg.toLocaleString(undefined, { maximumFractionDigits: 1 })} kg
        </div>
        <div className="stat-footer">
          <span>Awaiting analyst sign-off</span>
        </div>
      </div>
    </div>
  );
}
