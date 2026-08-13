import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Textarea } from '../components/ui/textarea';
import { toast } from 'sonner';
import { Users } from 'lucide-react';
import { usePatients } from '../../contexts/PatientContext';
import nhcxService from '../../services/nhcxService';
import { USE_CASES, loadFixture } from '../../services/fixtures';
import { buildCoverageEligibilityBundle, buildClaimBundle, buildTaskBundle } from '../../services/fhirBuilder';

export function SendRequestPage() {
  const { patients } = usePatients();
  const [selectedPatientId, setSelectedPatientId] = useState('');
  const selectedPatient = patients.find((p) => p.id === selectedPatientId);

  const [useCase, setUseCase] = useState('');
  const [recipientCode, setRecipientCode] = useState('1000003538@hcx');
  const [workflowId, setWorkflowId] = useState('12');
  const [correlationId, setCorrelationId] = useState('');
  const [fhirBundle, setFhirBundle] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);

  const handleBuildFromPatient = () => {
    if (!selectedPatient) return toast.error('Select a patient first');
    if (!useCase) return toast.error('Select a use case first');

    let bundle: Record<string, unknown>;
    if (useCase === 'coverageeligibility') {
      bundle = buildCoverageEligibilityBundle(selectedPatient);
    } else if (['preauth', 'claim', 'predetermination'].includes(useCase)) {
      bundle = buildClaimBundle(selectedPatient, useCase as 'preauthorization' | 'claim' | 'predetermination');
    } else {
      bundle = buildTaskBundle(selectedPatient, 'poll');
    }

    setFhirBundle(JSON.stringify(bundle, null, 2));
    const config = USE_CASES[useCase];
    if (config) setWorkflowId(config.workflowId);
    toast.success(`FHIR bundle built from ${selectedPatient.fullName}'s data`);
  };

  const handleLoadFixture = async () => {
    if (!useCase) return toast.error('Select a use case first');
    const bundle = await loadFixture(useCase);
    if (bundle) {
      setFhirBundle(JSON.stringify(bundle, null, 2));
      const config = USE_CASES[useCase];
      if (config) setWorkflowId(config.workflowId);
      toast.success('Fixture loaded');
    } else {
      toast.error('No fixture for this use case');
    }
  };

  const handleSend = async () => {
    if (!useCase) return toast.error('Select a use case');
    if (!fhirBundle) return toast.error('Load or build a FHIR bundle');
    let parsed: Record<string, unknown>;
    try {
      parsed = JSON.parse(fhirBundle);
    } catch {
      return toast.error('Invalid JSON in FHIR bundle');
    }
    setLoading(true);
    setResult(null);
    try {
      const config = USE_CASES[useCase];
      const resp = await nhcxService.sendRequest({
        hospitalId: '1000004604@hcx',
        useCase,
        endpoint: config?.endpoint || '',
        workflowId,
        recipientCode,
        fhirBundle: parsed,
        correlationId: correlationId || undefined,
        benAbhaId: selectedPatient?.abhaNumber || undefined,
      });
      setResult(resp);
      toast.success(`Request sent! Correlation ID: ${resp.correlationId?.slice(0, 16)}...`);
    } catch (e: any) {
      toast.error(e.message || 'Send failed');
      setResult({ error: e.message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Send Request</h1>
        <p className="text-sm text-muted-foreground">Submit FHIR bundles to the NHCX gateway</p>
      </div>

      {patients.length > 0 && (
        <Card className="border-primary/20 bg-primary/5">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <Users className="h-4 w-4" />
              Select Patient for FHIR Bundle
            </CardTitle>
            <CardDescription>
              Auto-build a FHIR bundle from the patient's onboarding data
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {patients.map((p) => (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => setSelectedPatientId(p.id)}
                  className={`flex items-center gap-2 rounded-lg border px-3 py-2 text-sm transition-colors ${
                    selectedPatientId === p.id
                      ? 'border-primary bg-primary/10 font-medium text-primary'
                      : 'border-border hover:bg-muted/60'
                  }`}
                >
                  <span>{p.fullName}</span>
                  <span className="text-xs text-muted-foreground">
                    {p.abhaNumber ? `ABHA: ${p.abhaNumber}` : ''}
                  </span>
                </button>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Request Configuration</CardTitle>
          <CardDescription>Select use case and configure the request parameters</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label>Use Case *</Label>
              <Select value={useCase} onValueChange={(v) => {
                setUseCase(v);
                const config = USE_CASES[v];
                if (config) setWorkflowId(config.workflowId);
              }}>
                <SelectTrigger><SelectValue placeholder="Select use case..." /></SelectTrigger>
                <SelectContent>
                  {Object.entries(USE_CASES).map(([key, cfg]) => (
                    <SelectItem key={key} value={key}>{cfg.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Workflow ID</Label>
              <Input value={workflowId} onChange={(e) => setWorkflowId(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>Recipient Code (Payer)</Label>
              <Input value={recipientCode} onChange={(e) => setRecipientCode(e.target.value)} placeholder="1000003538@hcx" />
            </div>
            <div className="space-y-2">
              <Label>Correlation ID (optional)</Label>
              <Input value={correlationId} onChange={(e) => setCorrelationId(e.target.value)} placeholder="UUID" />
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label>FHIR Bundle (JSON) *</Label>
              <div className="flex gap-2">
                {selectedPatient && (
                  <Button variant="outline" size="sm" onClick={handleBuildFromPatient}>
                    Build from Patient
                  </Button>
                )}
                <Button variant="outline" size="sm" onClick={handleLoadFixture}>Load Fixture</Button>
              </div>
            </div>
            <Textarea
              className="h-64 font-mono text-xs"
              placeholder='{"resourceType": "Bundle", "type": "collection", ...}'
              value={fhirBundle}
              onChange={(e) => setFhirBundle(e.target.value)}
            />
          </div>

          <Button onClick={handleSend} disabled={loading} className="w-full">
            {loading ? 'Sending...' : 'Send to NHCX Gateway'}
          </Button>
        </CardContent>
      </Card>

      {result && (
        <Card>
          <CardHeader>
            <CardTitle>{result.error ? 'Error' : 'Response'}</CardTitle>
          </CardHeader>
          <CardContent>
            <pre className="overflow-x-auto rounded bg-muted p-4 text-xs max-h-64 overflow-y-auto">{JSON.stringify(result, null, 2)}</pre>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
