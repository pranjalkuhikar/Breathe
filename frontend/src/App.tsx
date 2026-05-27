import React, { useState, useEffect } from 'react';
import { XCircle } from 'lucide-react';
import Sidebar from './components/Sidebar';
import KPIs from './components/KPIs';
import Charts from './components/Charts';
import RecordTable from './components/RecordTable';
import ReviewDrawer from './components/ReviewDrawer';
import IngestionPanel from './components/IngestionPanel';
import type { ActivityRecord, IngestionBatch, DashboardStats } from './types';
import './App.css';

// Load from environment variable with fallback
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api';

export default function App() {
  const [activeTab, setActiveTab] = useState<'dashboard' | 'ingest'>('dashboard');
  
  // State for dashboard
  const [records, setRecords] = useState<ActivityRecord[]>([]);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [batches, setBatches] = useState<IngestionBatch[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Filter States
  const [search, setSearch] = useState('');
  const [filterScope, setFilterScope] = useState('');
  const [filterStatus, setFilterStatus] = useState('');
  const [filterSource, setFilterSource] = useState('');
  
  // Detail Drawer State
  const [selectedRecord, setSelectedRecord] = useState<ActivityRecord | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  
  // Edit Form State
  const [editQuantity, setEditQuantity] = useState('');
  const [editCategory, setEditCategory] = useState('');
  const [editSuccessMessage, setEditSuccessMessage] = useState('');
  const [editErrorMessage, setEditErrorMessage] = useState('');
  
  // Custom Flagging State
  const [flagReasonInput, setFlagReasonInput] = useState('');
  const [showFlagInput, setShowFlagInput] = useState(false);
  
  // Ingest State
  const [selectedFileType, setSelectedFileType] = useState<'SAP' | 'UTILITY' | 'TRAVEL'>('SAP');
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadReport, setUploadReport] = useState<any | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  // Fetch initial dashboard and records data
  const fetchData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      // Build query string
      let queryParams = [];
      if (search) queryParams.push(`search=${encodeURIComponent(search)}`);
      if (filterScope) queryParams.push(`scope=${filterScope}`);
      if (filterStatus) queryParams.push(`status=${filterStatus}`);
      if (filterSource) queryParams.push(`source_type=${filterSource}`);
      
      const queryStr = queryParams.length > 0 ? `?${queryParams.join('&')}` : '';
      
      const [recordsRes, statsRes, batchesRes] = await Promise.all([
        fetch(`${API_BASE_URL}/records/${queryStr}`),
        fetch(`${API_BASE_URL}/dashboard-stats/${queryStr}`),
        fetch(`${API_BASE_URL}/batches/`)
      ]);
      
      if (!recordsRes.ok || !statsRes.ok || !batchesRes.ok) {
        throw new Error("Failed to fetch dashboard data. Please make sure the backend is running.");
      }
      
      const recordsData = await recordsRes.json();
      const statsData = await statsRes.json();
      const batchesData = await batchesRes.json();
      
      setRecords(recordsData);
      setStats(statsData);
      setBatches(batchesData);
    } catch (err: any) {
      setError(err.message || 'An error occurred.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [search, filterScope, filterStatus, filterSource]);

  // Handle Drawer Close
  const closeDrawer = () => {
    setIsDrawerOpen(false);
    setSelectedRecord(null);
    setEditQuantity('');
    setEditCategory('');
    setEditSuccessMessage('');
    setEditErrorMessage('');
    setShowFlagInput(false);
    setFlagReasonInput('');
  };

  // Open Record Details
  const handleRowClick = (rec: ActivityRecord) => {
    setSelectedRecord(rec);
    setEditQuantity(parseFloat(rec.normalized_quantity).toString());
    setEditCategory(rec.category);
    setIsDrawerOpen(true);
  };

  // Perform record action (approve, reject, flag)
  const handleRecordAction = async (actionType: 'approve' | 'reject' | 'flag') => {
    if (!selectedRecord) return;
    
    let body = {};
    if (actionType === 'flag') {
      if (!flagReasonInput.trim()) {
        setShowFlagInput(true);
        return;
      }
      body = { reason: flagReasonInput };
    }
    
    try {
      const res = await fetch(`${API_BASE_URL}/records/${selectedRecord.id}/${actionType}/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body)
      });
      
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.error || `Failed to perform action: ${actionType}`);
      }
      
      const updatedRec = await res.json();
      setSelectedRecord(updatedRec);
      
      // Update in locally loaded list
      setRecords(prev => prev.map(r => r.id === updatedRec.id ? updatedRec : r));
      setEditSuccessMessage(`Record successfully ${actionType}d.`);
      setShowFlagInput(false);
      setFlagReasonInput('');
      
      // Refresh Stats
      const statsRes = await fetch(`${API_BASE_URL}/dashboard-stats/`);
      if (statsRes.ok) {
        setStats(await statsRes.json());
      }
    } catch (err: any) {
      setEditErrorMessage(err.message);
    }
  };

  // Perform manual correction PUT
  const handleManualEdit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedRecord) return;
    
    setEditSuccessMessage('');
    setEditErrorMessage('');
    
    try {
      const res = await fetch(`${API_BASE_URL}/records/${selectedRecord.id}/`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          normalized_quantity: parseFloat(editQuantity),
          category: editCategory
        })
      });
      
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.error || 'Failed to update record.');
      }
      
      const updatedRec = await res.json();
      setSelectedRecord(updatedRec);
      setRecords(prev => prev.map(r => r.id === updatedRec.id ? updatedRec : r));
      setEditSuccessMessage('Quantity successfully corrected! CO2e recalculated.');
      
      // Refresh Stats
      const statsRes = await fetch(`${API_BASE_URL}/dashboard-stats/`);
      if (statsRes.ok) {
        setStats(await statsRes.json());
      }
    } catch (err: any) {
      setEditErrorMessage(err.message);
    }
  };

  // Ingest Form Submit
  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadFile) return;
    
    setIsUploading(true);
    setUploadReport(null);
    setError(null);
    
    const formData = new FormData();
    formData.append('file', uploadFile);
    formData.append('source_type', selectedFileType);
    
    try {
      const res = await fetch(`${API_BASE_URL}/ingest/`, {
        method: 'POST',
        body: formData
      });
      
      const data = await res.json();
      
      if (!res.ok) {
        throw new Error(data.error || 'Failed to process file ingestion.');
      }
      
      setUploadReport(data);
      setUploadFile(null);
      
      // Reload everything in background
      fetchData();
    } catch (err: any) {
      setError(err.message || 'Failed to upload and ingest file.');
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="app-container">
      {/* Sidebar navigation */}
      <Sidebar 
        activeTab={activeTab} 
        setActiveTab={setActiveTab} 
        closeDrawer={closeDrawer} 
      />

      {/* Main Panel */}
      <main className="main-content">
        {/* Header */}
        <header className="dashboard-header">
          <div className="header-title">
            <h1>{activeTab === 'dashboard' ? 'Review & Auditing' : 'ESG Data Ingestion'}</h1>
            <p>{activeTab === 'dashboard' ? 'Verify, correct, and approve activity records before audit locking.' : 'Onboard SAP reports, utility CSVs, and travel platform schedules.'}</p>
          </div>
        </header>

        {/* Global Error Banner */}
        {error && (
          <div className="warning-box fade-in" style={{ marginBottom: '24px', backgroundColor: 'hsl(var(--status-rejected) / 0.1)', borderColor: 'hsl(var(--status-rejected) / 0.3)' }}>
            <XCircle className="warning-icon" style={{ color: 'hsl(var(--status-rejected))' }} />
            <div className="warning-content">
              <h4 style={{ color: 'hsl(var(--status-rejected))' }}>Connection Error</h4>
              <p style={{ color: 'white' }}>{error}</p>
            </div>
          </div>
        )}

        {activeTab === 'dashboard' ? (
          <div className="fade-in">
            {/* KPI Cards */}
            {stats && <KPIs stats={stats} />}

            {/* Visual Charts panel */}
            {stats && <Charts stats={stats} />}

            {/* Filter and interactive table panel */}
            <RecordTable 
              records={records}
              search={search}
              setSearch={setSearch}
              filterScope={filterScope}
              setFilterScope={setFilterScope}
              filterStatus={filterStatus}
              setFilterStatus={setFilterStatus}
              filterSource={filterSource}
              setFilterSource={setFilterSource}
              handleRowClick={handleRowClick}
              isLoading={isLoading}
            />
          </div>
        ) : (
          /* Ingestion Page Tab */
          <IngestionPanel 
            selectedFileType={selectedFileType}
            setSelectedFileType={setSelectedFileType}
            uploadFile={uploadFile}
            setUploadFile={setUploadFile}
            isUploading={isUploading}
            uploadReport={uploadReport}
            setUploadReport={setUploadReport}
            isDragging={isDragging}
            setIsDragging={setIsDragging}
            handleUploadSubmit={handleUploadSubmit}
            batches={batches}
            setActiveTab={setActiveTab}
          />
        )}
      </main>

      {/* Slide-out Review Drawer */}
      <ReviewDrawer 
        isDrawerOpen={isDrawerOpen}
        closeDrawer={closeDrawer}
        selectedRecord={selectedRecord}
        editQuantity={editQuantity}
        setEditQuantity={setEditQuantity}
        editCategory={editCategory}
        setEditCategory={setEditCategory}
        editSuccessMessage={editSuccessMessage}
        editErrorMessage={editErrorMessage}
        handleManualEdit={handleManualEdit}
        handleRecordAction={handleRecordAction}
        showFlagInput={showFlagInput}
        setShowFlagInput={setShowFlagInput}
        flagReasonInput={flagReasonInput}
        setFlagReasonInput={setFlagReasonInput}
      />
    </div>
  );
}
