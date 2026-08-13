import { apiClient, buildUrl, ApiResponse } from './apiClient';
import { API_ENDPOINTS } from './apiConfig';

const BASE = API_ENDPOINTS.nhcx;

// ── Bridge API types ───────────────────────────────────────

export interface LogEntry {
  apiCallId: string;
  correlationId: string;
  useCase: string;
  state: string;
  direction: string;
  createdAt: string;
  recipientCode?: string;
  senderCode?: string;
  fhirBundleIn?: unknown;
  fhirBundleOut?: unknown;
}

export interface SendRequest {
  hospitalId: string;
  useCase: string;
  endpoint: string;
  workflowId: string;
  recipientCode: string;
  fhirBundle: Record<string, unknown>;
  correlationId?: string;
  benAbhaId?: string;
  claimNumber?: string;
  policyNumber?: string;
}

export interface SendResponse {
  correlationId: string;
  apiCallId: string;
  result?: Record<string, unknown>;
  error?: Record<string, unknown>;
}

export interface PolicyEntry {
  sno: string;
  abhanumber: string;
  mobilenumber: string;
  memberid: string;
  payerid: string;
  processingid: string;
  productid: string;
  productname: string;
}

// ── Marisha page types ─────────────────────────────────────

export type NhcxStatus =
  | 'draft'
  | 'preauthRequested'
  | 'preauthApproved'
  | 'preauthRejected'
  | 'claimSubmitted'
  | 'claimApproved'
  | 'claimRejected'
  | 'reprocessRequested';

export interface NhcxStatusEvent {
  status: NhcxStatus;
  at: string;
  note?: string;
  source?: 'manual' | 'nhcx_callback';
  by?: string;
}

export interface NhcxClaim {
  claimId: string;
  patientId: string;
  hospitalId?: string;
  category?: string;
  policyNumber?: string;
  insurerId?: string;
  diagnosisCode?: string;
  estimatedAmount?: number;
  finalAmount?: number;
  treatmentSummary?: string;
  invoiceId?: string;
  insurerReference?: string;
  status: NhcxStatus;
  statusHistory?: NhcxStatusEvent[];
  createdAt?: string;
  updatedAt?: string;
}

export interface PatientNhcxDetails {
  patientId: string;
  name?: string;
  abhaNumber?: string;
  abhaAddress?: string;
  uhid?: string;
  policyNumber?: string;
  insurerId?: string;
  insurerName?: string;
  coverageStatus?: string;
  recentClaims?: NhcxClaim[];
}

export interface CreatePreauthPayload {
  patientId: string;
  policyNumber?: string;
  insurerId?: string;
  diagnosisCode?: string;
  estimatedAmount?: number;
  category?: string;
  invoiceId?: string;
}

export interface SubmitClaimPayload {
  finalAmount?: number;
  treatmentSummary?: string;
  invoiceId?: string;
}

export interface EligibilityCheckPayload {
  patientId: string;
  policyNumber?: string;
  insurerId?: string;
  treatmentCode?: string;
  estimatedAmount?: number;
}

export interface EligibilityResult {
  eligible: boolean;
  coverageAmount?: number;
  remainingSumInsured?: number;
  notes?: string;
}

export interface CommunicationMessage {
  id: string;
  claimId: string;
  message: string;
  from: 'hospital' | 'insurer';
  at: string;
}

// ── Helpers ────────────────────────────────────────────────

async function unwrap<T>(promise: Promise<ApiResponse<T>>): Promise<T> {
  const res = await promise;
  const r = res as any;
  return r.data !== undefined ? r.data : r;
}

// In-memory store for marisha pages (claims, comms, etc.)
// Replace with real backend calls when endpoints are available.
const _claims: NhcxClaim[] = [];
const _comms: Record<string, CommunicationMessage[]> = {};
let _claimSeq = 1;

function _now() { return new Date().toISOString(); }
function _claimId() { return `CLM-${String(_claimSeq++).padStart(4, '0')}`; }

// ── Service ────────────────────────────────────────────────

const nhcxService = {
  // ── Bridge API (real endpoints) ────────────────────────

  listLogs: (limit = 50) =>
    unwrap<LogEntry[]>(apiClient.get<LogEntry[]>(buildUrl(BASE, '/logs', { limit }))),

  getLog: (apiCallId: string) =>
    unwrap<LogEntry>(apiClient.get<LogEntry>(buildUrl(BASE, `/logs/${apiCallId}`))),

  sendRequest: (req: SendRequest) =>
    unwrap<SendResponse>(apiClient.post<SendResponse>(buildUrl(BASE, '/send'), req)),

  getPolicies: (identifierType: string, identifierValue: string) =>
    unwrap<PolicyEntry[]>(
      apiClient.get<PolicyEntry[]>(buildUrl(BASE, '/sandbox/policies', { identifierType, identifierValue })),
    ),

  linkPolicy: (body: {
    abhanumber: string; mobilenumber: string; payerid: string;
    processingid: string; memberid: string;
    policies: Array<{ productid: string; productname: string }>;
  }) =>
    unwrap<{ ok: boolean; response: unknown }>(
      apiClient.post<{ ok: boolean; response: unknown }>(
        buildUrl(BASE, '/sandbox/policies/link'),
        { ...body, confirmSandboxMutation: true },
      ),
    ),

  delinkPolicy: (body: {
    payerid: string; memberid: string; processingid: string;
    policies: Array<{ productid: string; productname: string }>;
  }) =>
    unwrap<{ ok: boolean; response: unknown }>(
      apiClient.post<{ ok: boolean; response: unknown }>(
        buildUrl(BASE, '/sandbox/policies/delink'),
        { ...body, confirmSandboxMutation: true },
      ),
    ),

  dummyPayerProcess: (correlationId: string, action: string, method: string) =>
    unwrap<{ ok: boolean; response: unknown }>(
      apiClient.post<{ ok: boolean; response: unknown }>(
        buildUrl(BASE, '/sandbox/dummy-payer/process'),
        { correlationId, action, method },
      ),
    ),

  paymentNoticeInit: (correlationId: string) =>
    unwrap<{ ok: boolean; response: unknown }>(
      apiClient.post<{ ok: boolean; response: unknown }>(
        buildUrl(BASE, '/sandbox/dummy-payer/payment-notice'),
        { correlationId },
      ),
    ),

  statusCheck: (recipientCode: string, targetCorrelationId: string) =>
    unwrap<{ ok: boolean; response: unknown }>(
      apiClient.post<{ ok: boolean; response: unknown }>(
        buildUrl(BASE, '/sandbox/status-check'),
        { recipientCode, targetCorrelationId },
      ),
    ),

  listParticipants: (role: string, fromdate: string, todate: string) =>
    unwrap<{ ok: boolean; response: unknown }>(
      apiClient.get<{ ok: boolean; response: unknown }>(
        buildUrl(BASE, '/sandbox/participants', { role, fromdate, todate }),
      ),
    ),

  fetchCerts: (participantId: string) =>
    unwrap<{ ok: boolean; response: { encryption_cert?: string; signing_cert?: string } }>(
      apiClient.get<{ ok: boolean; response: { encryption_cert?: string; signing_cert?: string } }>(
        buildUrl(BASE, '/sandbox/certs', { participantId }),
      ),
    ),

  checkToken: () =>
    unwrap<{ ok: boolean; tokenPreview: string }>(
      apiClient.get<{ ok: boolean; tokenPreview: string }>(buildUrl(BASE, '/test0/token')),
    ),
  checkSelfCert: () =>
    unwrap<{ ok: boolean; response: unknown }>(
      apiClient.get<{ ok: boolean; response: unknown }>(buildUrl(BASE, '/test0/certs/self')),
    ),
  checkPayerCert: () =>
    unwrap<{ ok: boolean; response: unknown }>(
      apiClient.get<{ ok: boolean; response: unknown }>(buildUrl(BASE, '/test0/certs/payer')),
    ),

  // ── Marisha page methods (local stubs) ─────────────────
  // TODO: Replace with real backend endpoints when available

  getPatientDetails: async (patientId: string): Promise<{ data: PatientNhcxDetails }> => {
    const existing = _claims.find((c) => c.patientId === patientId);
    return {
      data: {
        patientId,
        name: patientId,
        recentClaims: existing ? [existing] : [],
      },
    };
  },

  list: async (params?: { status?: string; category?: string; pageSize?: number }): Promise<{ data: NhcxClaim[] }> => {
    let result = [..._claims];
    if (params?.status) result = result.filter((c) => c.status === params.status);
    if (params?.category) result = result.filter((c) => c.category === params.category);
    return { data: result };
  },

  getById: async (claimId: string): Promise<{ data: NhcxClaim }> => {
    const claim = _claims.find((c) => c.claimId === claimId);
    if (!claim) throw new Error('Claim not found');
    return { data: claim };
  },

  createPreauth: async (data: CreatePreauthPayload): Promise<{ data: NhcxClaim }> => {
    const claim: NhcxClaim = {
      claimId: _claimId(),
      patientId: data.patientId,
      category: data.category,
      policyNumber: data.policyNumber,
      insurerId: data.insurerId,
      diagnosisCode: data.diagnosisCode,
      estimatedAmount: data.estimatedAmount,
      status: 'preauthRequested',
      statusHistory: [{ status: 'preauthRequested', at: _now(), source: 'manual' }],
      createdAt: _now(),
    };
    _claims.unshift(claim);
    return { data: claim };
  },

  submitClaim: async (claimId: string, data: SubmitClaimPayload): Promise<{ data: NhcxClaim }> => {
    const claim = _claims.find((c) => c.claimId === claimId);
    if (!claim) throw new Error('Claim not found');
    claim.finalAmount = data.finalAmount;
    claim.treatmentSummary = data.treatmentSummary;
    claim.status = 'claimSubmitted';
    claim.statusHistory?.push({ status: 'claimSubmitted', at: _now(), source: 'manual' });
    claim.updatedAt = _now();
    return { data: claim };
  },

  updateStatus: async (claimId: string, status: NhcxStatus, note?: string): Promise<{ data: NhcxClaim }> => {
    const claim = _claims.find((c) => c.claimId === claimId);
    if (!claim) throw new Error('Claim not found');
    claim.status = status;
    claim.statusHistory?.push({ status, at: _now(), note, source: 'manual' });
    claim.updatedAt = _now();
    return { data: claim };
  },

  checkEligibility: async (data: EligibilityCheckPayload): Promise<{ data: EligibilityResult }> => {
    return {
      data: {
        eligible: true,
        coverageAmount: 500000,
        remainingSumInsured: 350000,
        notes: 'Coverage verified for patient ' + data.patientId,
      },
    };
  },

  listCommunications: async (claimId: string): Promise<{ data: CommunicationMessage[] }> => {
    return { data: _comms[claimId] || [] };
  },

  sendCommunication: async (claimId: string, message: string): Promise<{ data: CommunicationMessage }> => {
    if (!_comms[claimId]) _comms[claimId] = [];
    const msg: CommunicationMessage = {
      id: `MSG-${Date.now()}`,
      claimId,
      message,
      from: 'hospital',
      at: _now(),
    };
    _comms[claimId].push(msg);
    return { data: msg };
  },

  requestReprocess: async (claimId: string, reason?: string): Promise<{ data: NhcxClaim }> => {
    const claim = _claims.find((c) => c.claimId === claimId);
    if (!claim) throw new Error('Claim not found');
    claim.status = 'reprocessRequested';
    claim.statusHistory?.push({ status: 'reprocessRequested', at: _now(), note: reason, source: 'manual' });
    claim.updatedAt = _now();
    return { data: claim };
  },
};

export default nhcxService;
