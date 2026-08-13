import { useEffect, useState } from 'react';
import { Search, ShieldCheck, FileText, CheckCircle2, XCircle, Clock, Send, MessageSquare, RefreshCw, User, Users } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Badge } from '../components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../components/ui/dialog';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '../components/ui/table';
import { toast } from 'sonner';
import { usePermissions } from '../../hooks/usePermissions';
import { usePatients, PatientRegistration } from '../../contexts/PatientContext';
import nhcxService, {
  NhcxClaim, NhcxStatus, PatientNhcxDetails, EligibilityResult, CommunicationMessage,
} from '../../services/nhcxService';

const STATUS_OPTIONS: { value: NhcxStatus; label: string }[] = [
  { value: 'draft', label: 'Draft' },
  { value: 'preauthRequested', label: 'Preauth Requested' },
  { value: 'preauthApproved', label: 'Preauth Approved' },
  { value: 'preauthRejected', label: 'Preauth Rejected' },
  { value: 'claimSubmitted', label: 'Claim Submitted' },
  { value: 'claimApproved', label: 'Claim Approved' },
  { value: 'claimRejected', label: 'Claim Rejected' },
  { value: 'reprocessRequested', label: 'Reprocess Requested' },
];

const CATEGORY_OPTIONS = ['cashless', 'reimbursement'];

function StatusBadge({ status }: { status: NhcxStatus }) {
  const config: Record<NhcxStatus, { icon: any; className: string }> = {
    draft: { icon: Clock, className: 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200' },
    preauthRequested: { icon: Clock, className: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200' },
    preauthApproved: { icon: CheckCircle2, className: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' },
    preauthRejected: { icon: XCircle, className: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200' },
    claimSubmitted: { icon: Send, className: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200' },
    claimApproved: { icon: CheckCircle2, className: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' },
    claimRejected: { icon: XCircle, className: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200' },
    reprocessRequested: { icon: RefreshCw, className: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200' },
  };
  const { icon: Icon, className } = config[status] || config.draft;
  return (
    <Badge className={className}>
      <Icon className="h-3 w-3 mr-1" />
      {STATUS_OPTIONS.find(s => s.value === status)?.label || status}
    </Badge>
  );
}

export function NhcxPage() {
  const { isAdmin } = usePermissions();
  const { patients } = usePatients();

  // Selected patient for auto-fill
  const [selectedPatientId, setSelectedPatientId] = useState('');
  const selectedPatient = patients.find((p) => p.id === selectedPatientId);

  // Auto-fill from selected patient
  const autoFillFromPatient = (p: PatientRegistration) => {
    setSelectedPatientId(p.id);
    setEligPatientId(p.abhaNumber || p.aadhaarNumber || p.id);
    setPreauthPatientId(p.abhaNumber || p.aadhaarNumber || p.id);
    setPolicyNumber(p.policyNumber);
    setInsurerId(p.insurerRegNumber || p.insurerName);
    setDiagnosisCode(p.diagnoses[0]?.code || '');
  };

  // Patient lookup
  const [patientId, setPatientId] = useState('');
  const [patientDetails, setPatientDetails] = useState<PatientNhcxDetails | null>(null);
  const [loadingPatient, setLoadingPatient] = useState(false);

  // Coverage eligibility check
  const [eligPatientId, setEligPatientId] = useState('');
  const [eligTreatmentCode, setEligTreatmentCode] = useState('');
  const [eligAmount, setEligAmount] = useState('');
  const [eligResult, setEligResult] = useState<EligibilityResult | null>(null);
  const [checkingElig, setCheckingElig] = useState(false);

  // Preauth form
  const [preauthPatientId, setPreauthPatientId] = useState('');
  const [category, setCategory] = useState('cashless');
  const [policyNumber, setPolicyNumber] = useState('');
  const [insurerId, setInsurerId] = useState('');
  const [diagnosisCode, setDiagnosisCode] = useState('');
  const [estimatedAmount, setEstimatedAmount] = useState('');
  const [submittingPreauth, setSubmittingPreauth] = useState(false);

  // List + filters
  const [claims, setClaims] = useState<NhcxClaim[]>([]);
  const [loadingClaims, setLoadingClaims] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');

  // Detail dialog
  const [selectedClaim, setSelectedClaim] = useState<NhcxClaim | null>(null);
  const [finalAmount, setFinalAmount] = useState('');
  const [treatmentSummary, setTreatmentSummary] = useState('');
  const [actionNote, setActionNote] = useState('');
  const [actionLoading, setActionLoading] = useState(false);

  // Communication thread (per selected claim)
  const [communications, setCommunications] = useState<CommunicationMessage[]>([]);
  const [loadingComms, setLoadingComms] = useState(false);
  const [commMessage, setCommMessage] = useState('');
  const [sendingComm, setSendingComm] = useState(false);

  // Reprocess request
  const [reprocessReason, setReprocessReason] = useState('');
  const [reprocessLoading, setReprocessLoading] = useState(false);

  const loadClaims = async () => {
    setLoadingClaims(true);
    try {
      const res = await nhcxService.list({
        status: statusFilter === 'all' ? undefined : statusFilter,
        category: categoryFilter === 'all' ? undefined : categoryFilter,
        pageSize: 50,
      });
      setClaims(res.data || []);
    } catch (err: any) {
      toast.error(err.message || 'Failed to load claims');
    } finally {
      setLoadingClaims(false);
    }
  };

  useEffect(() => {
    loadClaims();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter, categoryFilter]);

  const handleLookupPatient = async () => {
    if (!patientId.trim()) {
      toast.error('Enter a patient ID');
      return;
    }
    setLoadingPatient(true);
    try {
      const res = await nhcxService.getPatientDetails(patientId.trim());
      setPatientDetails(res.data);
    } catch (err: any) {
      toast.error(err.message || 'Could not fetch patient NHCX details');
      setPatientDetails(null);
    } finally {
      setLoadingPatient(false);
    }
  };

  const handleCheckEligibility = async () => {
    if (!eligPatientId.trim()) {
      toast.error('Enter a patient ID');
      return;
    }
    setCheckingElig(true);
    try {
      const res = await nhcxService.checkEligibility({
        patientId: eligPatientId.trim(),
        treatmentCode: eligTreatmentCode || undefined,
        estimatedAmount: eligAmount ? Number(eligAmount) : undefined,
      });
      setEligResult(res.data);
    } catch (err: any) {
      toast.error(err.message || 'Eligibility check failed');
      setEligResult(null);
    } finally {
      setCheckingElig(false);
    }
  };

  const handleCreatePreauth = async () => {
    if (!preauthPatientId.trim()) {
      toast.error('Patient ID is required');
      return;
    }
    setSubmittingPreauth(true);
    try {
      await nhcxService.createPreauth({
        patientId: preauthPatientId.trim(),
        category,
        policyNumber: policyNumber || undefined,
        insurerId: insurerId || undefined,
        diagnosisCode: diagnosisCode || undefined,
        estimatedAmount: estimatedAmount ? Number(estimatedAmount) : undefined,
      });
      toast.success('Pre-authorization request raised');
      setPreauthPatientId('');
      setPolicyNumber('');
      setInsurerId('');
      setDiagnosisCode('');
      setEstimatedAmount('');
      loadClaims();
    } catch (err: any) {
      toast.error(err.message || 'Failed to raise preauth request');
    } finally {
      setSubmittingPreauth(false);
    }
  };

  const openClaim = (claim: NhcxClaim) => {
    setSelectedClaim(claim);
    setFinalAmount(claim.estimatedAmount ? String(claim.estimatedAmount) : '');
    setTreatmentSummary('');
    setActionNote('');
    setCommMessage('');
    setReprocessReason('');
    loadCommunications(claim.claimId);
  };

  const loadCommunications = async (claimId: string) => {
    setLoadingComms(true);
    try {
      const res = await nhcxService.listCommunications(claimId);
      setCommunications(res.data || []);
    } catch (err: any) {
      toast.error(err.message || 'Failed to load communication thread');
    } finally {
      setLoadingComms(false);
    }
  };

  const handleSendCommunication = async () => {
    if (!selectedClaim || !commMessage.trim()) return;
    setSendingComm(true);
    try {
      await nhcxService.sendCommunication(selectedClaim.claimId, commMessage.trim());
      setCommMessage('');
      loadCommunications(selectedClaim.claimId);
    } catch (err: any) {
      toast.error(err.message || 'Failed to send message');
    } finally {
      setSendingComm(false);
    }
  };

  const handleRequestReprocess = async () => {
    if (!selectedClaim) return;
    setReprocessLoading(true);
    try {
      const res = await nhcxService.requestReprocess(selectedClaim.claimId, reprocessReason || undefined);
      toast.success('Reprocess request sent');
      setSelectedClaim(res.data);
      setReprocessReason('');
      loadClaims();
    } catch (err: any) {
      toast.error(err.message || 'Failed to request reprocess');
    } finally {
      setReprocessLoading(false);
    }
  };

  const handleSubmitClaim = async () => {
    if (!selectedClaim) return;
    setActionLoading(true);
    try {
      const res = await nhcxService.submitClaim(selectedClaim.claimId, {
        finalAmount: finalAmount ? Number(finalAmount) : undefined,
        treatmentSummary: treatmentSummary || undefined,
      });
      toast.success('Claim submitted');
      setSelectedClaim(res.data);
      loadClaims();
    } catch (err: any) {
      toast.error(err.message || 'Failed to submit claim');
    } finally {
      setActionLoading(false);
    }
  };

  const handleUpdateStatus = async (status: NhcxStatus) => {
    if (!selectedClaim) return;
    setActionLoading(true);
    try {
      const res = await nhcxService.updateStatus(selectedClaim.claimId, status, actionNote || undefined);
      toast.success(`Marked as ${STATUS_OPTIONS.find(s => s.value === status)?.label}`);
      setSelectedClaim(res.data);
      setActionNote('');
      loadClaims();
    } catch (err: any) {
      toast.error(err.message || 'Failed to update status');
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div className="p-4 sm:p-6 space-y-4 sm:space-y-6">
      <div>
        <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white">NHCX Claims</h1>
        <p className="text-gray-500 dark:text-gray-400">
          Patient coverage lookup, pre-authorization, claim submission, and status tracking
        </p>
      </div>

      {/* Patient Selector — picks a registered patient to auto-fill all forms */}
      {patients.length > 0 && (
        <Card className="border-primary/20 bg-primary/5">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <User className="h-4 w-4" />
              Select Registered Patient
            </CardTitle>
            <CardDescription>
              Pick a patient from onboarding to auto-fill eligibility, preauth, and claim forms
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {patients.map((p) => (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => autoFillFromPatient(p)}
                  className={`flex items-center gap-2 rounded-lg border px-3 py-2 text-sm transition-colors ${
                    selectedPatientId === p.id
                      ? 'border-primary bg-primary/10 font-medium text-primary'
                      : 'border-border hover:bg-muted/60'
                  }`}
                >
                  {p.patientPhoto?.previewUrl ? (
                    <img src={p.patientPhoto.previewUrl} alt={p.fullName} className="h-6 w-6 rounded-full object-cover" />
                  ) : (
                    <Users className="h-4 w-4 text-muted-foreground" />
                  )}
                  <span>{p.fullName}</span>
                  <span className="text-xs text-muted-foreground">
                    {p.abhaNumber ? `ABHA: ${p.abhaNumber}` : p.policyNumber ? `Policy: ${p.policyNumber}` : ''}
                  </span>
                </button>
              ))}
            </div>
            {selectedPatient && (
              <div className="mt-3 flex flex-wrap gap-4 text-sm text-muted-foreground">
                <span><strong>Hospital:</strong> {selectedPatient.hospitalName || '—'}</span>
                <span><strong>Insurer:</strong> {selectedPatient.insurerName || '—'}</span>
                <span><strong>Policy:</strong> {selectedPatient.policyNumber || '—'}</span>
                <span><strong>Diagnosis:</strong> {selectedPatient.diagnoses[0]?.display || '—'}</span>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Patient NHCX Lookup */}
      <Card>
        <CardHeader>
          <CardTitle>Patient NHCX Details</CardTitle>
          <CardDescription>Look up a patient's coverage and recent claim history</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-2">
            <Input
              placeholder="Patient ID"
              value={patientId}
              onChange={(e) => setPatientId(e.target.value)}
            />
            <Button onClick={handleLookupPatient} disabled={loadingPatient} className="gap-2 shrink-0">
              <Search className="h-4 w-4" />
              {loadingPatient ? 'Looking up...' : 'Lookup'}
            </Button>
          </div>

          {patientDetails && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-2 border-t">
              <div>
                <p className="text-xs text-gray-500">Name</p>
                <p className="font-medium">{patientDetails.name || '—'}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">ABHA Number</p>
                <p className="font-medium">{patientDetails.abhaNumber || '—'}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Insurer</p>
                <p className="font-medium">{patientDetails.insurerName || '—'}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Policy Number</p>
                <p className="font-medium">{patientDetails.policyNumber || '—'}</p>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Coverage Eligibility Check */}
      <Card>
        <CardHeader>
          <CardTitle>Check Coverage Eligibility</CardTitle>
          <CardDescription>Verify a treatment is covered before raising a preauth request</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label>Patient ID</Label>
              <Input value={eligPatientId} onChange={(e) => setEligPatientId(e.target.value)} placeholder="Patient ID" />
            </div>
            <div className="space-y-2">
              <Label>Treatment Code</Label>
              <Input value={eligTreatmentCode} onChange={(e) => setEligTreatmentCode(e.target.value)} placeholder="e.g. procedure/ICD code" />
            </div>
            <div className="space-y-2">
              <Label>Estimated Amount</Label>
              <Input type="number" value={eligAmount} onChange={(e) => setEligAmount(e.target.value)} placeholder="0" />
            </div>
          </div>
          <Button className="gap-2" onClick={handleCheckEligibility} disabled={checkingElig}>
            <ShieldCheck className="h-4 w-4" />
            {checkingElig ? 'Checking...' : 'Check Eligibility'}
          </Button>

          {eligResult && (
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 pt-2 border-t">
              <div>
                <p className="text-xs text-gray-500">Eligible</p>
                <p className="font-medium">
                  {eligResult.eligible ? (
                    <span className="text-green-700 dark:text-green-400 flex items-center gap-1"><CheckCircle2 className="h-4 w-4" /> Yes</span>
                  ) : (
                    <span className="text-red-700 dark:text-red-400 flex items-center gap-1"><XCircle className="h-4 w-4" /> No</span>
                  )}
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Coverage Amount</p>
                <p className="font-medium">{eligResult.coverageAmount ?? '—'}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Remaining Sum Insured</p>
                <p className="font-medium">{eligResult.remainingSumInsured ?? '—'}</p>
              </div>
              {eligResult.notes && (
                <div className="col-span-2 sm:col-span-3">
                  <p className="text-xs text-gray-500">Notes</p>
                  <p className="text-sm">{eligResult.notes}</p>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Raise Preauth */}
      <Card>
        <CardHeader>
          <CardTitle>Raise Pre-Authorization Request</CardTitle>
          <CardDescription>Start a new cashless or reimbursement claim</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label>Patient ID</Label>
              <Input value={preauthPatientId} onChange={(e) => setPreauthPatientId(e.target.value)} placeholder="Patient ID" />
            </div>
            <div className="space-y-2">
              <Label>Category</Label>
              <Select value={category} onValueChange={setCategory}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {CATEGORY_OPTIONS.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Estimated Amount</Label>
              <Input type="number" value={estimatedAmount} onChange={(e) => setEstimatedAmount(e.target.value)} placeholder="0" />
            </div>
            <div className="space-y-2">
              <Label>Policy Number</Label>
              <Input value={policyNumber} onChange={(e) => setPolicyNumber(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>Insurer ID</Label>
              <Input value={insurerId} onChange={(e) => setInsurerId(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>Diagnosis Code</Label>
              <Input value={diagnosisCode} onChange={(e) => setDiagnosisCode(e.target.value)} />
            </div>
          </div>
          <Button className="mt-4 gap-2" onClick={handleCreatePreauth} disabled={submittingPreauth}>
            <ShieldCheck className="h-4 w-4" />
            {submittingPreauth ? 'Submitting...' : 'Raise Preauth Request'}
          </Button>
        </CardContent>
      </Card>

      {/* List + Filters */}
      <Card>
        <CardHeader>
          <CardTitle>Claims</CardTitle>
          <CardDescription>Filter by status or category</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-3">
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-[200px]"><SelectValue placeholder="All statuses" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All statuses</SelectItem>
                {STATUS_OPTIONS.map(s => <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>)}
              </SelectContent>
            </Select>
            <Select value={categoryFilter} onValueChange={setCategoryFilter}>
              <SelectTrigger className="w-[200px]"><SelectValue placeholder="All categories" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All categories</SelectItem>
                {CATEGORY_OPTIONS.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>

          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Claim ID</TableHead>
                <TableHead>Patient ID</TableHead>
                <TableHead>Category</TableHead>
                <TableHead>Amount</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Created</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {claims.length === 0 && !loadingClaims && (
                <TableRow><TableCell colSpan={7} className="text-center text-gray-500">No claims found</TableCell></TableRow>
              )}
              {claims.map((claim) => (
                <TableRow key={claim.claimId}>
                  <TableCell className="font-mono text-xs">{claim.claimId}</TableCell>
                  <TableCell>{claim.patientId}</TableCell>
                  <TableCell className="capitalize">{claim.category || '—'}</TableCell>
                  <TableCell>{claim.finalAmount ?? claim.estimatedAmount ?? '—'}</TableCell>
                  <TableCell><StatusBadge status={claim.status} /></TableCell>
                  <TableCell>{claim.createdAt ? new Date(claim.createdAt).toLocaleDateString() : '—'}</TableCell>
                  <TableCell>
                    <Button size="sm" variant="outline" className="gap-1" onClick={() => openClaim(claim)}>
                      <FileText className="h-3 w-3" /> View
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Detail Dialog */}
      <Dialog open={!!selectedClaim} onOpenChange={(open) => !open && setSelectedClaim(null)}>
        <DialogContent className="max-w-2xl">
          {selectedClaim && (
            <>
              <DialogHeader>
                <DialogTitle className="flex items-center gap-2">
                  Claim {selectedClaim.claimId}
                  <StatusBadge status={selectedClaim.status} />
                </DialogTitle>
                <DialogDescription>
                  Patient: {selectedClaim.patientId} • Category: {selectedClaim.category || '—'}
                </DialogDescription>
              </DialogHeader>

              <div className="space-y-4">
                {/* Status timeline */}
                <div>
                  <p className="text-sm font-medium mb-2">Status History</p>
                  <div className="space-y-2">
                    {(selectedClaim.statusHistory || []).map((event, idx) => (
                      <div key={idx} className="flex items-start gap-2 text-sm">
                        <StatusBadge status={event.status} />
                        <div className="text-gray-500">
                          {event.at ? new Date(event.at).toLocaleString() : ''} {event.note ? `— ${event.note}` : ''}
                        </div>
                      </div>
                    ))}
                    {(!selectedClaim.statusHistory || selectedClaim.statusHistory.length === 0) && (
                      <p className="text-sm text-gray-500">No history yet</p>
                    )}
                  </div>
                </div>

                {/* Submit claim — only once preauth is approved */}
                {selectedClaim.status === 'preauthApproved' && (
                  <div className="space-y-2 pt-2 border-t">
                    <p className="text-sm font-medium">Submit Final Claim</p>
                    <div className="grid grid-cols-2 gap-3">
                      <div className="space-y-1">
                        <Label>Final Amount</Label>
                        <Input type="number" value={finalAmount} onChange={(e) => setFinalAmount(e.target.value)} />
                      </div>
                      <div className="space-y-1 col-span-2">
                        <Label>Treatment Summary</Label>
                        <Textarea value={treatmentSummary} onChange={(e) => setTreatmentSummary(e.target.value)} />
                      </div>
                    </div>
                    <Button onClick={handleSubmitClaim} disabled={actionLoading} className="gap-2">
                      <Send className="h-4 w-4" /> Submit Claim
                    </Button>
                  </div>
                )}

                {/* Communication Request — query/response thread with the insurer */}
                <div className="space-y-2 pt-2 border-t">
                  <p className="text-sm font-medium flex items-center gap-2">
                    <MessageSquare className="h-4 w-4" /> Communication
                  </p>
                  <div className="space-y-2 max-h-40 overflow-y-auto">
                    {loadingComms && <p className="text-sm text-gray-500">Loading...</p>}
                    {!loadingComms && communications.length === 0 && (
                      <p className="text-sm text-gray-500">No messages yet</p>
                    )}
                    {communications.map((msg) => (
                      <div key={msg.id} className="text-sm">
                        <span className="font-medium capitalize">{msg.from}: </span>
                        <span>{msg.message}</span>
                        <span className="text-gray-500 text-xs ml-2">
                          {msg.at ? new Date(msg.at).toLocaleString() : ''}
                        </span>
                      </div>
                    ))}
                  </div>
                  <div className="flex gap-2">
                    <Input
                      placeholder="Send a query to the insurer..."
                      value={commMessage}
                      onChange={(e) => setCommMessage(e.target.value)}
                    />
                    <Button size="sm" className="gap-1 shrink-0" onClick={handleSendCommunication} disabled={sendingComm}>
                      <Send className="h-3 w-3" /> Send
                    </Button>
                  </div>
                </div>

                {/* Reprocess Request — ask the insurer to re-review a rejected claim */}
                {(selectedClaim.status === 'preauthRejected' || selectedClaim.status === 'claimRejected') && (
                  <div className="space-y-2 pt-2 border-t">
                    <p className="text-sm font-medium flex items-center gap-2">
                      <RefreshCw className="h-4 w-4" /> Request Reprocess
                    </p>
                    <Textarea
                      placeholder="Reason for reprocess request"
                      value={reprocessReason}
                      onChange={(e) => setReprocessReason(e.target.value)}
                    />
                    <Button variant="outline" className="gap-2" onClick={handleRequestReprocess} disabled={reprocessLoading}>
                      <RefreshCw className="h-4 w-4" /> {reprocessLoading ? 'Sending...' : 'Request Reprocess'}
                    </Button>
                  </div>
                )}

                {/* Manual approve/reject stub — Admin only, standing in for the
                    real NHCX callback until sandbox access exists */}
                {isAdmin && ['preauthRequested', 'claimSubmitted'].includes(selectedClaim.status) && (
                  <div className="space-y-2 pt-2 border-t">
                    <p className="text-sm font-medium">
                      {selectedClaim.status === 'preauthRequested' ? 'Preauth Decision (manual, until NHCX sandbox access)' : 'Claim Decision (manual, until NHCX sandbox access)'}
                    </p>
                    <Textarea placeholder="Note (optional)" value={actionNote} onChange={(e) => setActionNote(e.target.value)} />
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        className="gap-2"
                        disabled={actionLoading}
                        onClick={() => handleUpdateStatus(selectedClaim.status === 'preauthRequested' ? 'preauthApproved' : 'claimApproved')}
                      >
                        <CheckCircle2 className="h-4 w-4" /> Approve
                      </Button>
                      <Button
                        variant="outline"
                        className="gap-2 text-red-600"
                        disabled={actionLoading}
                        onClick={() => handleUpdateStatus(selectedClaim.status === 'preauthRequested' ? 'preauthRejected' : 'claimRejected')}
                      >
                        <XCircle className="h-4 w-4" /> Reject
                      </Button>
                    </div>
                  </div>
                )}
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
