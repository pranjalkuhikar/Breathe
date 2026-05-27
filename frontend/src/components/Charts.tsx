import { Info } from 'lucide-react';
import type { DashboardStats } from '../types';

interface ChartsProps {
  stats: DashboardStats;
}

export default function Charts({ stats }: ChartsProps) {
  return (
    <div className="charts-grid">
      {/* Scope breakdown bar chart */}
      <div className="panel">
        <div className="panel-header">
          <h2 className="panel-title">Emissions Breakdown by Scope</h2>
          <Info size={16} style={{ color: 'hsl(var(--text-secondary))' }} />
        </div>
        <div className="visual-bar-chart">
          {Object.entries(stats.scopes).map(([scopeKey, scopeVal]) => {
            const fillClass = scopeKey === 'Scope 1' ? 'scope1-bar' : scopeKey === 'Scope 2' ? 'scope2-bar' : 'scope3-bar';
            return (
              <div className="bar-row" key={scopeKey}>
                <div className="bar-labels">
                  <span className="bar-label-name">
                    {scopeKey} - {scopeKey === 'Scope 1' ? 'Direct Combustion' : scopeKey === 'Scope 2' ? 'Indirect Energy' : 'Value Chain'}
                  </span>
                  <span>
                    {scopeVal.co2e.toLocaleString(undefined, { maximumFractionDigits: 1 })} kg CO2e ({scopeVal.percentage}%)
                  </span>
                </div>
                <div className="bar-track">
                  <div className={`bar-fill ${fillClass}`} style={{ width: `${scopeVal.percentage}%` }}></div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Top Emitting centers */}
      <div className="panel">
        <div className="panel-header">
          <h2 className="panel-title">Top 3 Facilities</h2>
        </div>
        <div className="visual-bar-chart">
          {stats.top_facilities.slice(0, 3).map((item, idx) => (
            <div className="bar-row" key={idx}>
              <div className="bar-labels">
                <span 
                  className="bar-label-name" 
                  style={{ textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap', maxWidth: '140px' }}
                >
                  {item.facility}
                </span>
                <span>{item.co2e.toLocaleString(undefined, { maximumFractionDigits: 0 })} kg</span>
              </div>
              <div className="bar-track" style={{ height: '6px' }}>
                <div 
                  className="bar-fill" 
                  style={{ 
                    width: `${stats.total_co2e_kg > 0 ? (item.co2e / stats.total_co2e_kg) * 100 : 0}%`, 
                    backgroundColor: '#a855f7' 
                  }}
                ></div>
              </div>
            </div>
          ))}
          {stats.top_facilities.length === 0 && (
            <div style={{ color: 'hsl(var(--text-secondary))', textAlign: 'center', fontSize: '13px', padding: '20px' }}>
              No facility data mapped yet.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
