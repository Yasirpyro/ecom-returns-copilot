// API Configuration - Base URL configurable via environment variable
const rawBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const API_BASE_URL = rawBaseUrl.replace(/\/+$/, '');

const REVIEWER_AUTH_KEY = 'reviewer_basic_auth';

export function setReviewerAuth(username: string, password: string) {
  const token = btoa(`${username}:${password}`);
  sessionStorage.setItem(REVIEWER_AUTH_KEY, `Basic ${token}`);
}

export function clearReviewerAuth() {
  sessionStorage.removeItem(REVIEWER_AUTH_KEY);
}

function getReviewerAuthHeader(): Record<string, string> {
  const auth = sessionStorage.getItem(REVIEWER_AUTH_KEY);
  return auth ? { Authorization: auth } : {};
}

// Types
export interface ChatStartResponse {
  session_id: string;
}

export interface ChatMessage {
  message: string;
  order_id?: string;
  reason?: string;
  wants_store_credit?: boolean;
  photos_provided?: boolean;
}

export interface ChatResponse {
  session_id: string;
  assistant_message: string;
  case_id: string | null;
  status: 'needs_customer_photos' | 'ready_for_human_review' | 'approved' | 'denied' | 'more_info_requested' | 'closed' | null;
}

export interface OrderItem {
  sku: string;
  qty: number;
  unit_price: number;
  is_final_sale: boolean;
  warranty_days: number;
  product: {
    name: string;
    category?: string;
  };
}

export interface OrderFacts {
  order_id: string;
  delivered_at: string;
  shipping_method: string;
  outbound_shipping_paid: number;
  items: OrderItem[];
}

export interface PolicyCitation {
  source: string;
  excerpt: string;
  policy_id: string;
}

export interface Case {
  case_id: string;
  order_id: string;
  reason: string;
  status: string;
  created_at: string;
  photos_required: boolean;
  ai_decision_json: Record<string, unknown>;
  policy_citations_json: PolicyCitation[];
  order_facts_json: OrderFacts;
  photo_urls_json: string[];
  human_decision: string | null;
  human_notes: string | null;
  final_customer_reply: string | null;
  next_actions_json: Array<{ action: string; details?: string }>;
  customer_message?: string;
}

export interface CasePublicStatus {
  case_id: string;
  status: string | null;
  final_customer_reply: string | null;
  next_actions_json: Array<{ action: string; details?: string }> | null;
}

export interface CasesListResponse {
  data: Case[];
}

export interface PhotoUploadResponse {
  case_id: string;
  photo_url: string;
}

export interface DecisionResponse {
  case_id: string;
  status: string;
}

export interface FinalizeResponse {
  case_id: string;
  status: string;
  customer_reply: string;
  next_actions: Array<{ action: string; details?: string }>;
}

// API Functions
export async function startChat(): Promise<ChatStartResponse> {
  const response = await fetch(`${API_BASE_URL}/chat/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!response.ok) throw new Error('Failed to start chat session');
  return response.json();
}

export async function sendMessage(sessionId: string, message: ChatMessage): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE_URL}/chat/${sessionId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(message),
  });
  if (!response.ok) throw new Error('Failed to send message');
  return response.json();
}

export async function getCases(status?: string): Promise<CasesListResponse> {
  const url = status 
    ? `${API_BASE_URL}/cases?status=${encodeURIComponent(status)}`
    : `${API_BASE_URL}/cases`;
  const response = await fetch(url, { headers: { ...getReviewerAuthHeader() } });
  if (!response.ok) throw new Error('Failed to fetch cases');
  return response.json();
}

export async function getCase(caseId: string): Promise<Case> {
  const response = await fetch(`${API_BASE_URL}/cases/${caseId}`, {
    headers: { ...getReviewerAuthHeader() },
  });
  if (!response.ok) throw new Error('Failed to fetch case');
  return response.json();
}

export async function getCasePublic(caseId: string): Promise<CasePublicStatus> {
  const response = await fetch(`${API_BASE_URL}/cases/${caseId}/public`);
  if (!response.ok) throw new Error('Failed to fetch case status');
  return response.json();
}

export async function uploadPhoto(caseId: string, file: File): Promise<PhotoUploadResponse> {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await fetch(`${API_BASE_URL}/cases/${caseId}/photos`, {
    method: 'POST',
    body: formData,
  });
  if (!response.ok) throw new Error('Failed to upload photo');
  return response.json();
}

export async function submitDecision(
  caseId: string, 
  decision: 'approved' | 'denied' | 'more_info_requested',
  notes?: string
): Promise<DecisionResponse> {
  const url = new URL(`${API_BASE_URL}/cases/${caseId}/decision`);
  url.searchParams.set('decision', decision);
  if (notes) url.searchParams.set('notes', notes);
  
  const response = await fetch(url.toString(), {
    method: 'POST',
    headers: { ...getReviewerAuthHeader() },
  });
  if (!response.ok) throw new Error('Failed to submit decision');
  return response.json();
}

export async function finalizeCase(caseId: string): Promise<FinalizeResponse> {
  const response = await fetch(`${API_BASE_URL}/cases/${caseId}/finalize`, {
    method: 'POST',
    headers: { ...getReviewerAuthHeader() },
  });
  if (!response.ok) throw new Error('Failed to finalize case');
  return response.json();
}
