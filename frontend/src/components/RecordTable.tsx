import { Search, ShieldCheck, AlertTriangle } from 'lucide-react';
import type { ActivityRecord } from '../types';

interface RecordTableProps {
  records: ActivityRecord[];
  search: string;
  setSearch: (s: string) => void;
  filterScope: string;
  setFilterScope: (s: string) => void;
  filterStatus: string;
  setFilterStatus: (s: string) => void;
  filterSource: string;
  setFilterSource: (s: string) => void;
  handleRowClick: (rec: ActivityRecord) => void;
  isLoading: boolean;
}

export default function RecordTable({
  records,
  search,
  setSearch,
  filterScope,
  setFilterScope,
  filterStatus,
  setFilterStatus,
  filterSource,
  setFilterSource,
  handleRowClick,
  isLoading
}: RecordTableProps) {
  return (
    <div className="panel">
      <div className="filter-bar">
        <div className="search-input-wrapper">
          <Search className="search-icon" size={16} />
          <input 
            type="text"
            className="search-input"
            placeholder="Search by Facility, Category, or description..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <div className="filters-group">
          <select 
            className="select-filter"
            value={filterSource}
            onChange={(e) => setFilterSource(e.target.value)}
          >
            <option value="">All Sources</option>
            <option value="SAP">SAP Fuel</option>
            <option value="UTILITY">Utility Electricity</option>
            <option value="TRAVEL">Corporate Travel</option>
          </select>

          <select 
            className="select-filter"
            value={filterScope}
            onChange={(e) => setFilterScope(e.target.value)}
          >
            <option value="">All Scopes</option>
            <option value="1">Scope 1</option>
            <option value="2">Scope 2</option>
            <option value="3">Scope 3</option>
          </select>

          <select 
            className="select-filter"
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
          >
            <option value="">All Statuses</option>
            <option value="PENDING">Pending</option>
            <option value="APPROVED">Approved & Locked</option>
            <option value="FLAGGED">Flagged</option>
            <option value="REJECTED">Rejected</option>
          </select>
        </div>
      </div>

      {/* Data Table Grid */}
      <div className="data-table-container">
        <table className="esg-table">
          <thead>
            <tr>
              <th>Date</th>
              <th>Source</th>
              <th>Facility/Meter</th>
              <th>Scope</th>
              <th>Category</th>
              <th>Raw Qty</th>
              <th>Normalized Usage</th>
              <th>Carbon Computed</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {records.map((rec) => (
              <tr 
                key={rec.id} 
                onClick={() => handleRowClick(rec)}
                className={rec.status === 'FLAGGED' ? 'flagged-row' : ''}
              >
                <td>{rec.transaction_date}</td>
                <td>
                  <div className="source-icon-badge">
                    <span className={`source-indicator ${rec.batch_detail.source_type.toLowerCase()}`}></span>
                    <span>{rec.batch_detail.source_type}</span>
                  </div>
                </td>
                <td style={{ fontWeight: '500' }}>{rec.facility_name}</td>
                <td>
                  <span className={`scope-badge scope${rec.scope}`}>Scope {rec.scope}</span>
                </td>
                <td>{rec.category}</td>
                <td style={{ color: 'hsl(var(--text-secondary))' }}>
                  {parseFloat(rec.raw_quantity || '0').toLocaleString(undefined, { maximumFractionDigits: 1 })} {rec.raw_unit}
                </td>
                <td style={{ fontWeight: '500' }}>
                  {parseFloat(rec.normalized_quantity).toLocaleString(undefined, { maximumFractionDigits: 1 })} {rec.normalized_unit}
                </td>
                <td style={{ fontWeight: '600', color: 'white' }}>
                  {parseFloat(rec.co2e_kg).toLocaleString(undefined, { maximumFractionDigits: 1 })} kg CO2e
                </td>
                <td>
                  <span className={`status-badge ${rec.status.toLowerCase()}`}>
                    {rec.status === 'APPROVED' ? <ShieldCheck size={12} /> : null}
                    {rec.status === 'FLAGGED' ? <AlertTriangle size={12} /> : null}
                    {rec.status}
                  </span>
                </td>
              </tr>
            ))}
            {records.length === 0 && (
              <tr>
                <td colSpan={9} style={{ textAlign: 'center', padding: '40px', color: 'hsl(var(--text-secondary))' }}>
                  {isLoading ? 'Loading ESG activity logs...' : 'No activity records match filters.'}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
