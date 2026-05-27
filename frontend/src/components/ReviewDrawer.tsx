import React from 'react';
import { X, AlertTriangle, ShieldCheck, Edit3, UserCheck, XCircle } from 'lucide-react';
import type { ActivityRecord } from '../types';

interface ReviewDrawerProps {
  isDrawerOpen: boolean;
  closeDrawer: () => void;
  selectedRecord: ActivityRecord | null;
  editQuantity: string;
  setEditQuantity: (s: string) => void;
  editCategory: string;
  setEditCategory: (s: string) => void;
  editSuccessMessage: string;
  editErrorMessage: string;
  handleManualEdit: (e: React.FormEvent) => void;
  handleRecordAction: (actionType: 'approve' | 'reject' | 'flag') => void;
  showFlagInput: boolean;
  setShowFlagInput: (b: boolean) => void;
  flagReasonInput: string;
  setFlagReasonInput: (s: string) => void;
}

export default function ReviewDrawer({
  isDrawerOpen,
  closeDrawer,
  selectedRecord,
  editQuantity,
  setEditQuantity,
  editCategory,
  setEditCategory,
  editSuccessMessage,
  editErrorMessage,
  handleManualEdit,
  handleRecordAction,
  showFlagInput,
  setShowFlagInput,
  flagReasonInput,
  setFlagReasonInput
}: ReviewDrawerProps) {
  if (!selectedRecord) return null;

  return (
    <div 
      className={`drawer-overlay ${isDrawerOpen ? 'open' : ''}`}
      onClick={closeDrawer}
    >
      <div 
        className="review-drawer"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Drawer Header */}
        <div className="drawer-header">
          <div>
            <h2 style={{ fontSize: '20px', fontWeight: '700' }}>Review & Adjust Record</h2>
            <p style={{ color: 'hsl(var(--text-secondary))', fontSize: '13px', marginTop: '2px' }}>
              Record #{selectedRecord.id} &bull; row {selectedRecord.source_row_index} of {selectedRecord.batch_detail.file_name}
            </p>
          </div>
          <button className="drawer-close" onClick={closeDrawer}>
            <X size={20} />
          </button>
        </div>

        {/* Drawer Body */}
        <div className="drawer-body">
          {/* 1. Suspicious Flags list */}
          {selectedRecord.status === 'FLAGGED' && (
            <div className="warning-box">
              <AlertTriangle className="warning-icon" />
              <div className="warning-content">
                <h4>Outlier & Validation Flags</h4>
                <ul>
                  {selectedRecord.flag_reasons.map((reason, rIdx) => (
                    <li key={rIdx}>{reason}</li>
                  ))}
                </ul>
              </div>
            </div>
          )}

          {/* 2. Raw vs Normalized details cards */}
          <div className="comparison-grid">
            {/* Left: Raw */}
            <div className="comparison-card">
              <h3>Raw Imported Row</h3>
              <div className="data-row">
                <span className="data-label">Plant/Facility Code</span>
                <span className="data-val">
                  {selectedRecord.raw_data.werks || selectedRecord.raw_data.facility || selectedRecord.raw_data.facility_name || 'N/A'}
                </span>
              </div>
              <div className="data-row">
                <span className="data-label">Raw Material/Type</span>
                <span className="data-val">
                  {selectedRecord.raw_data.matnr || selectedRecord.raw_data.category || selectedRecord.raw_data.travel_type || 'N/A'}
                </span>
              </div>
              <div className="data-row">
                <span className="data-label">Raw Input Quantity</span>
                <span className="data-val">
                  {parseFloat(selectedRecord.raw_quantity || '0').toLocaleString()} {selectedRecord.raw_unit}
                </span>
              </div>
              <div className="data-row">
                <span className="data-label">Date String</span>
                <span className="data-val">
                  {selectedRecord.raw_data.budat || selectedRecord.raw_data.start_date || selectedRecord.raw_data.date || 'N/A'}
                </span>
              </div>
              <div style={{ marginTop: '12px' }}>
                <span className="data-label" style={{ fontSize: '11px', display: 'block', marginBottom: '6px' }}>Complete Raw JSON:</span>
                <pre className="json-raw">{JSON.stringify(selectedRecord.raw_data, null, 2)}</pre>
              </div>
            </div>

            {/* Right: Normalized */}
            <div className="comparison-card">
              <h3>Normalized Scope Record</h3>
              <div className="data-row">
                <span className="data-label">Auditable Facility</span>
                <span className="data-val">{selectedRecord.facility_name}</span>
              </div>
              <div className="data-row">
                <span className="data-label">Scope Allocation</span>
                <span className="data-val" style={{ fontWeight: '600' }}>Scope {selectedRecord.scope}</span>
              </div>
              <div className="data-row">
                <span className="data-label">Normalized Category</span>
                <span className="data-val">{selectedRecord.category}</span>
              </div>
              <div className="data-row">
                <span className="data-label">Standard Quantity</span>
                <span className="data-val" style={{ color: 'white', fontWeight: '600' }}>
                  {parseFloat(selectedRecord.normalized_quantity).toLocaleString()} {selectedRecord.normalized_unit}
                </span>
              </div>
              <div className="data-row" style={{ backgroundColor: 'hsl(var(--color-primary) / 0.1)', padding: '10px 8px', borderRadius: '4px' }}>
                <span className="data-label" style={{ color: 'hsl(var(--color-primary))', fontWeight: '600' }}>Carbon Footprint</span>
                <span className="data-val" style={{ color: 'white', fontWeight: '700' }}>
                  {parseFloat(selectedRecord.co2e_kg).toLocaleString(undefined, { maximumFractionDigits: 2 })} kg CO2e
                </span>
              </div>
              <div className="data-row">
                <span className="data-label">Calendar Date</span>
                <span className="data-val">{selectedRecord.transaction_date}</span>
              </div>
              {selectedRecord.billing_start_date && (
                <div className="data-row">
                  <span className="data-label">Billing Period</span>
                  <span className="data-val" style={{ fontSize: '12px' }}>
                    {selectedRecord.billing_start_date} to {selectedRecord.billing_end_date}
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* 3. In-place Edit Manual Correction */}
          {!selectedRecord.locked_for_audit ? (
            <form onSubmit={handleManualEdit} className="edit-form-panel">
              <h3>Correct Normalized Values</h3>
              <div className="comparison-grid">
                <div className="form-group">
                  <label>Corrected Quantity ({selectedRecord.normalized_unit})</label>
                  <input 
                    type="number"
                    step="any"
                    className="form-input"
                    value={editQuantity}
                    onChange={(e) => setEditQuantity(e.target.value)}
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Adjustment Category</label>
                  <select 
                    className="form-input"
                    value={editCategory}
                    onChange={(e) => setEditCategory(e.target.value)}
                    required
                  >
                    <option value="Diesel Combustion">Diesel Combustion (Scope 1)</option>
                    <option value="Natural Gas Combustion">Natural Gas Combustion (Scope 1)</option>
                    <option value="Fuel Oil Combustion">Fuel Oil Combustion (Scope 1)</option>
                    <option value="Electricity Grid Consumption">Electricity Grid Consumption (Scope 2)</option>
                    <option value="Business Travel (Flights)">Business Travel - Flights (Scope 3)</option>
                    <option value="Business Travel (Hotels)">Business Travel - Hotels (Scope 3)</option>
                    <option value="Business Travel (Ground)">Business Travel - Ground (Scope 3)</option>
                  </select>
                </div>
              </div>
              
              <button 
                type="submit" 
                className="btn btn-secondary" 
                style={{ width: '100%', marginTop: '12px', fontSize: '13px', padding: '8px' }}
              >
                <Edit3 size={14} />
                Recalculate & Save Adjustments
              </button>
              
              {editSuccessMessage && (
                <div style={{ color: 'hsl(var(--status-approved))', fontSize: '12px', fontWeight: '500', marginTop: '8px', textAlign: 'center' }}>
                  {editSuccessMessage}
                </div>
              )}
              {editErrorMessage && (
                <div style={{ color: 'hsl(var(--status-rejected))', fontSize: '12px', fontWeight: '500', marginTop: '8px', textAlign: 'center' }}>
                  {editErrorMessage}
                </div>
              )}
            </form>
          ) : (
            <div className="warning-box" style={{ backgroundColor: 'hsl(var(--status-approved) / 0.08)', borderColor: 'hsl(var(--status-approved) / 0.3)' }}>
              <ShieldCheck className="warning-icon" style={{ color: 'hsl(var(--status-approved))' }} />
              <div className="warning-content">
                <h4 style={{ color: 'hsl(var(--status-approved))' }}>Approved & Locked for Audit</h4>
                <p style={{ color: 'white', fontSize: '12px' }}>
                  This record was signed off by **{selectedRecord.approved_by_name}** on **{new Date(selectedRecord.approved_at || '').toLocaleString()}**. 
                  Manual modifications are permanently disabled.
                </p>
              </div>
            </div>
          )}

          {/* 4. Audit Trail Timeline */}
          <div style={{ marginTop: '12px' }}>
            <h3 style={{ fontSize: '13px', fontWeight: '600', textTransform: 'uppercase', color: 'hsl(var(--text-secondary))', marginBottom: '16px' }}>
              Audit History log
            </h3>
            <div className="audit-timeline">
              {selectedRecord.audit_trail.map((log, lIdx) => (
                <div className="timeline-item" key={lIdx}>
                  <div className={`timeline-dot ${log.action.toLowerCase()}`}></div>
                  <div className="timeline-content">
                    <span className="timeline-action">
                      {log.action === 'CREATE' ? 'System Ingested Row' : null}
                      {log.action === 'APPROVE' ? 'Approved & Audit-Locked' : null}
                      {log.action === 'FLAG' ? 'Marked as Suspicious' : null}
                      {log.action === 'REJECT' ? 'Rejected Row' : null}
                      {log.action === 'UPDATE' ? 'Manual Value Correction' : null}
                    </span>
                    <span style={{ color: 'hsl(var(--text-secondary))' }}> by </span>
                    <span style={{ fontWeight: '500' }}>{log.user_name || 'System'}</span>
                    
                    {log.action === 'UPDATE' && (
                      <div style={{ fontSize: '11px', color: 'hsl(var(--text-secondary))', backgroundColor: 'rgba(0,0,0,0.15)', padding: '6px', borderRadius: '4px', marginTop: '4px' }}>
                        Qty: {parseFloat(log.previous_values.normalized_quantity).toLocaleString()} &rarr; {parseFloat(log.new_values.normalized_quantity).toLocaleString()} &bull; 
                        CO2: {parseFloat(log.previous_values.co2e_kg).toLocaleString(undefined, { maximumFractionDigits: 1 })} kg &rarr; {parseFloat(log.new_values.co2e_kg).toLocaleString(undefined, { maximumFractionDigits: 1 })} kg
                      </div>
                    )}
                    
                    {log.action === 'FLAG' && log.new_values.flag_reasons && (
                      <div style={{ fontSize: '11px', color: 'hsl(var(--status-flagged))', marginTop: '2px' }}>
                        Reason: "{log.new_values.flag_reasons[log.new_values.flag_reasons.length - 1]}"
                      </div>
                    )}
                    
                    <div className="timeline-meta">{new Date(log.timestamp).toLocaleString()}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Drawer Actions */}
        {!selectedRecord.locked_for_audit && (
          <div className="drawer-actions">
            <button 
              className="btn btn-primary"
              style={{ flexGrow: 2 }}
              onClick={() => handleRecordAction('approve')}
            >
              <UserCheck size={16} />
              Approve & Lock
            </button>
            
            <button 
              className="btn btn-warning"
              style={{ flexGrow: 1 }}
              onClick={() => {
                if (showFlagInput) {
                  handleRecordAction('flag');
                } else {
                  setShowFlagInput(true);
                }
              }}
            >
              <AlertTriangle size={16} />
              {showFlagInput ? 'Submit Flag' : 'Flag Suspicious'}
            </button>

            <button 
              className="btn btn-danger"
              style={{ flexGrow: 1 }}
              onClick={() => handleRecordAction('reject')}
            >
              <XCircle size={16} />
              Reject
            </button>
          </div>
        )}

        {/* Drawer Flag Reason Input Modal-like Block */}
        {showFlagInput && (
          <div style={{ padding: '0 24px 24px', backgroundColor: 'hsl(var(--bg-surface))', borderTop: '1px solid hsl(var(--border-subtle))' }}>
            <div className="form-group" style={{ marginTop: '12px' }}>
              <label style={{ color: 'hsl(var(--status-flagged))', fontWeight: '500' }}>Suspicious Flag Reason</label>
              <textarea
                className="form-input"
                style={{ width: '100%', height: '60px', marginTop: '6px', resize: 'none' }}
                placeholder="Explain why this row is suspicious (e.g. meter reads are uncalibrated)..."
                value={flagReasonInput}
                onChange={(e) => setFlagReasonInput(e.target.value)}
              />
            </div>
            <div style={{ display: 'flex', gap: '12px', marginTop: '12px' }}>
              <button 
                className="btn btn-primary" 
                style={{ flexGrow: 1, padding: '8px' }}
                onClick={() => handleRecordAction('flag')}
              >
                Flag Row
              </button>
              <button 
                className="btn btn-secondary" 
                style={{ flexGrow: 1, padding: '8px' }}
                onClick={() => setShowFlagInput(false)}
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
