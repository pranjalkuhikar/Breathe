import React, { useRef } from 'react';
import { Upload, Flame, FileSpreadsheet, Plane, CheckCircle, ArrowRight } from 'lucide-react';
import type { IngestionBatch } from '../types';

interface IngestionPanelProps {
  selectedFileType: 'SAP' | 'UTILITY' | 'TRAVEL';
  setSelectedFileType: (type: 'SAP' | 'UTILITY' | 'TRAVEL') => void;
  uploadFile: File | null;
  setUploadFile: (f: File | null) => void;
  isUploading: boolean;
  uploadReport: any | null;
  setUploadReport: (r: any | null) => void;
  isDragging: boolean;
  setIsDragging: (b: boolean) => void;
  handleUploadSubmit: (e: React.FormEvent) => void;
  batches: IngestionBatch[];
  setActiveTab: (tab: 'dashboard' | 'ingest') => void;
}

export default function IngestionPanel({
  selectedFileType,
  setSelectedFileType,
  uploadFile,
  setUploadFile,
  isUploading,
  uploadReport,
  setUploadReport,
  isDragging,
  setIsDragging,
  handleUploadSubmit,
  batches,
  setActiveTab
}: IngestionPanelProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      setUploadFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setUploadFile(e.target.files[0]);
    }
  };

  return (
    <div className="fade-in">
      <div className="panel" style={{ maxWidth: '800px', margin: '0 auto' }}>
        <div className="panel-header">
          <h2 className="panel-title">Upload and Ingest Activity Schedule</h2>
        </div>
        
        <form onSubmit={handleUploadSubmit}>
          <div style={{ display: 'flex', gap: '24px', marginBottom: '24px' }}>
            <div style={{ flexGrow: 1 }} className="form-group">
              <label>Select Data Source Type</label>
              <div style={{ display: 'flex', gap: '12px', marginTop: '6px' }}>
                <button
                  type="button"
                  className={`btn ${selectedFileType === 'SAP' ? 'btn-primary' : 'btn-secondary'}`}
                  style={{ flexGrow: 1 }}
                  onClick={() => { setSelectedFileType('SAP'); setUploadReport(null); }}
                >
                  <Flame size={16} />
                  SAP Fuel
                </button>
                <button
                  type="button"
                  className={`btn ${selectedFileType === 'UTILITY' ? 'btn-primary' : 'btn-secondary'}`}
                  style={{ flexGrow: 1 }}
                  onClick={() => { setSelectedFileType('UTILITY'); setUploadReport(null); }}
                >
                  <FileSpreadsheet size={16} />
                  Utility Electricity
                </button>
                <button
                  type="button"
                  className={`btn ${selectedFileType === 'TRAVEL' ? 'btn-primary' : 'btn-secondary'}`}
                  style={{ flexGrow: 1 }}
                  onClick={() => { setSelectedFileType('TRAVEL'); setUploadReport(null); }}
                >
                  <Plane size={16} />
                  Corporate Travel
                </button>
              </div>
            </div>
          </div>

          <div 
            className={`upload-dropzone ${isDragging ? 'dragging' : ''}`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
          >
            <input 
              type="file" 
              ref={fileInputRef} 
              style={{ display: 'none' }} 
              accept=".csv"
              onChange={handleFileSelect}
            />
            <Upload className="upload-icon" size={40} />
            <div>
              <h3 className="upload-title">
                {uploadFile ? uploadFile.name : `Select or drag and drop your ${selectedFileType} export CSV`}
              </h3>
              <p className="upload-desc">Supports flat exports, automatic header-mapping, and outlier scans.</p>
            </div>
            {uploadFile && (
              <button 
                type="button" 
                className="btn btn-secondary" 
                onClick={(e) => { e.stopPropagation(); setUploadFile(null); }}
              >
                Clear File
              </button>
            )}
          </div>

          <button 
            type="submit" 
            className="btn btn-primary" 
            style={{ width: '100%', marginTop: '24px' }}
            disabled={!uploadFile || isUploading}
          >
            {isUploading ? 'Ingesting and Parsing Data...' : 'Start Ingestion Engine'}
          </button>
        </form>

        {/* Upload Report Summary */}
        {uploadReport && (
          <div 
            className="warning-box fade-in" 
            style={{ marginTop: '24px', backgroundColor: 'hsl(var(--status-approved) / 0.1)', borderColor: 'hsl(var(--status-approved) / 0.3)' }}
          >
            <CheckCircle className="warning-icon" style={{ color: 'hsl(var(--status-approved))' }} />
            <div className="warning-content">
              <h4 style={{ color: 'hsl(var(--status-approved))' }}>Ingestion Completed Successfully</h4>
              <p style={{ color: 'white', fontSize: '13px', marginTop: '4px' }}>
                Successfully parsed **{uploadReport.successful_rows}** valid rows. Found **{uploadReport.failed_rows}** row failures (logged to batch debug panel).
              </p>
              <button 
                className="btn btn-secondary" 
                style={{ padding: '6px 12px', fontSize: '11px', marginTop: '10px' }}
                onClick={() => { setActiveTab('dashboard'); }}
              >
                View in Dashboard
                <ArrowRight size={12} />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Upload History Batches */}
      <div className="batches-panel" style={{ maxWidth: '800px', margin: '32px auto 0' }}>
        <h2 className="panel-title" style={{ marginBottom: '16px' }}>Ingestion History</h2>
        {batches.map((b) => (
          <div className="batch-row" key={b.id}>
            <div className="batch-info">
              <span className="batch-name">{b.file_name}</span>
              <span className="batch-meta">
                Ingested {b.source_type} batch on {new Date(b.created_at).toLocaleString()}
              </span>
            </div>
            <div className="batch-counts">
              <span className="batch-success-count">{b.successful_rows} succeeded</span>
              {b.failed_rows > 0 ? (
                <span className="batch-fail-count">{b.failed_rows} failed</span>
              ) : null}
              <span className={`status-badge ${b.status.toLowerCase()}`}>{b.status}</span>
            </div>
          </div>
        ))}
        {batches.length === 0 && (
          <div style={{ color: 'hsl(var(--text-secondary))', textAlign: 'center', padding: '30px' }}>No files uploaded yet.</div>
        )}
      </div>
    </div>
  );
}
