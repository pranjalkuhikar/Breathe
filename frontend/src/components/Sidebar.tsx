import { BarChart3, ClipboardList, Upload } from 'lucide-react';

interface SidebarProps {
  activeTab: 'dashboard' | 'ingest';
  setActiveTab: (tab: 'dashboard' | 'ingest') => void;
  closeDrawer: () => void;
}

export default function Sidebar({ activeTab, setActiveTab, closeDrawer }: SidebarProps) {
  return (
    <aside className="sidebar">
      <div className="logo-container">
        <BarChart3 className="logo-icon" size={28} />
        <span className="logo-text">Breathe ESG</span>
      </div>
      
      <nav className="nav-links">
        <button 
          className={`nav-item ${activeTab === 'dashboard' ? 'active' : ''}`}
          onClick={() => { setActiveTab('dashboard'); closeDrawer(); }}
        >
          <ClipboardList size={18} />
          <span>Review Dashboard</span>
        </button>
        
        <button 
          className={`nav-item ${activeTab === 'ingest' ? 'active' : ''}`}
          onClick={() => { setActiveTab('ingest'); closeDrawer(); }}
        >
          <Upload size={18} />
          <span>Data Ingestion</span>
        </button>
      </nav>
      
      <div className="user-profile">
        <div className="avatar">A</div>
        <div className="user-info">
          <p className="name">ESG Analyst</p>
          <p className="role">Breathe ESG Corp</p>
        </div>
      </div>
    </aside>
  );
}
