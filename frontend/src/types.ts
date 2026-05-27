export interface AuditLog {
  id: number;
  action: string;
  user_name: string;
  previous_values: any;
  new_values: any;
  timestamp: string;
}

export interface IngestionBatch {
  id: number;
  source_type: 'SAP' | 'UTILITY' | 'TRAVEL';
  file_name: string;
  status: 'PENDING' | 'PROCESSED' | 'FAILED';
  total_rows: number;
  successful_rows: number;
  failed_rows: number;
  created_at: string;
}

export interface ActivityRecord {
  id: number;
  batch: number;
  batch_detail: IngestionBatch;
  source_row_index: number;
  scope: '1' | '2' | '3';
  category: string;
  description: string;
  facility_name: string;
  raw_quantity: string;
  raw_unit: string;
  normalized_quantity: string;
  normalized_unit: string;
  co2e_kg: string;
  status: 'PENDING' | 'APPROVED' | 'FLAGGED' | 'REJECTED';
  flag_reasons: string[];
  billing_start_date: string | null;
  billing_end_date: string | null;
  transaction_date: string;
  raw_data: any;
  approved_by_name: string | null;
  approved_at: string | null;
  locked_for_audit: boolean;
  audit_trail: AuditLog[];
  created_at: string;
}

export interface DashboardStats {
  total_co2e_kg: number;
  approved_co2e_kg: number;
  pending_co2e_kg: number;
  flagged_co2e_kg: number;
  total_records: number;
  flagged_records_count: number;
  approved_records_count: number;
  flagged_rate_pct: number;
  approval_rate_pct: number;
  scopes: {
    [key: string]: {
      co2e: number;
      count: number;
      percentage: number;
    };
  };
  sources: Array<{
    source: string;
    co2e: number;
    count: number;
    percentage: number;
  }>;
  batches: {
    [key: string]: number;
  };
  monthly_trends: Array<{
    month: string;
    co2e: number;
  }>;
  top_facilities: Array<{
    facility: string;
    co2e: number;
  }>;
}
