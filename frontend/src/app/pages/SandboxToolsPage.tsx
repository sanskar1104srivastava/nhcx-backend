import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { toast } from 'sonner';
import nhcxService from '../../services/nhcxService';

export function SandboxToolsPage() {
  // Dummy payer
  const [corrId, setCorrId] = useState('');
  const [action, setAction] = useState('Approve');
  const [method, setMethod] = useState('Preauth');
  const [payerResult, setPayerResult] = useState<any>(null);
  const [payerLoading, setPayerLoading] = useState(false);

  // Status check
  const [statusRecipient, setStatusRecipient] = useState('1000003538@hcx');
  const [statusCorrId, setStatusCorrId] = useState('');
  const [statusResult, setStatusResult] = useState<any>(null);
  const [statusLoading, setStatusLoading] = useState(false);

  // Cert lookup
  const [certParticipantId, setCertParticipantId] = useState('');
  const [certResult, setCertResult] = useState<any>(null);
  const [certLoading, setCertLoading] = useState(false);

  // Participant list
  const [participantRole, setParticipantRole] = useState('10001');
  const [participantFrom, setParticipantFrom] = useState('01/01/2024');
  const [participantTo, setParticipantTo] = useState('31/12/2026');
  const [participantResult, setParticipantResult] = useState<any>(null);
  const [participantLoading, setParticipantLoading] = useState(false);

  const handleDummyPayer = async () => {
    if (!corrId) return toast.error('Enter a correlation ID');
    setPayerLoading(true);
    try {
      const data = await nhcxService.dummyPayerProcess(corrId, action, method);
      setPayerResult(data);
      toast.success(`Dummy payer ${action} triggered`);
    } catch (e: any) {
      toast.error(e.message || 'Failed');
      setPayerResult({ error: e.message });
    } finally {
      setPayerLoading(false);
    }
  };

  const handleStatusCheck = async () => {
    if (!statusCorrId) return toast.error('Enter a correlation ID');
    setStatusLoading(true);
    try {
      const data = await nhcxService.statusCheck(statusRecipient, statusCorrId);
      setStatusResult(data);
      toast.success('Status check sent');
    } catch (e: any) {
      toast.error(e.message || 'Failed');
      setStatusResult({ error: e.message });
    } finally {
      setStatusLoading(false);
    }
  };

  const handleCertLookup = async () => {
    if (!certParticipantId) return toast.error('Enter a participant ID');
    setCertLoading(true);
    try {
      const data = await nhcxService.fetchCerts(certParticipantId);
      setCertResult(data);
      toast.success('Certificate fetched');
    } catch (e: any) {
      toast.error(e.message || 'Failed');
      setCertResult({ error: e.message });
    } finally {
      setCertLoading(false);
    }
  };

  const handleParticipantList = async () => {
    setParticipantLoading(true);
    try {
      const data = await nhcxService.listParticipants(participantRole, participantFrom, participantTo);
      setParticipantResult(data);
      toast.success('Participants fetched');
    } catch (e: any) {
      toast.error(e.message || 'Failed');
      setParticipantResult({ error: e.message });
    } finally {
      setParticipantLoading(false);
    }
  };

  const ResultBlock = ({ data }: { data: any }) => data ? (
    <pre className="mt-3 overflow-x-auto rounded bg-muted p-3 text-xs max-h-64 overflow-y-auto">{JSON.stringify(data, null, 2)}</pre>
  ) : null;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Sandbox Tools</h1>
        <p className="text-sm text-muted-foreground">Dummy payer actions, status checks, and participant lookups</p>
      </div>

      <Tabs defaultValue="payer">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="payer">Dummy Payer</TabsTrigger>
          <TabsTrigger value="status">Status Check</TabsTrigger>
          <TabsTrigger value="certs">Certificates</TabsTrigger>
          <TabsTrigger value="participants">Participants</TabsTrigger>
        </TabsList>

        <TabsContent value="payer" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle>Dummy Payer Actions</CardTitle>
              <CardDescription>Trigger the sandbox dummy payer to approve, reject, or query a request</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label>Correlation ID *</Label>
                <Input value={corrId} onChange={(e) => setCorrId(e.target.value)} placeholder="UUID of the request to act on" />
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label>Action</Label>
                  <Select value={action} onValueChange={setAction}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Approve">Approve</SelectItem>
                      <SelectItem value="Reject">Reject</SelectItem>
                      <SelectItem value="Query">Query</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Method</Label>
                  <Select value={method} onValueChange={setMethod}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Preauth">Preauth</SelectItem>
                      <SelectItem value="Claim">Claim</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <Button onClick={handleDummyPayer} disabled={payerLoading}>{payerLoading ? 'Triggering...' : 'Trigger Action'}</Button>
              <ResultBlock data={payerResult} />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="status" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle>Status Check</CardTitle>
              <CardDescription>Check the status of a previously sent request</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2"><Label>Recipient Code</Label><Input value={statusRecipient} onChange={(e) => setStatusRecipient(e.target.value)} /></div>
                <div className="space-y-2"><Label>Target Correlation ID *</Label><Input value={statusCorrId} onChange={(e) => setStatusCorrId(e.target.value)} placeholder="UUID" /></div>
              </div>
              <Button onClick={handleStatusCheck} disabled={statusLoading}>{statusLoading ? 'Checking...' : 'Check Status'}</Button>
              <ResultBlock data={statusResult} />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="certs" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle>Certificate Lookup</CardTitle>
              <CardDescription>Fetch the encryption certificate for a participant</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2"><Label>Participant ID</Label>
                <div className="flex gap-2">
                  <Input value={certParticipantId} onChange={(e) => setCertParticipantId(e.target.value)} placeholder="1000003538@hcx" />
                  <Button onClick={handleCertLookup} disabled={certLoading}>{certLoading ? 'Fetching...' : 'Fetch'}</Button>
                </div>
              </div>
              <ResultBlock data={certResult} />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="participants" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle>Participant List</CardTitle>
              <CardDescription>List registered participants by role and date range</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 sm:grid-cols-3">
                <div className="space-y-2"><Label>Role</Label>
                  <Select value={participantRole} onValueChange={setParticipantRole}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="10001">Provider</SelectItem>
                      <SelectItem value="10002">Payer</SelectItem>
                      <SelectItem value="10003">TPA</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2"><Label>From Date</Label><Input value={participantFrom} onChange={(e) => setParticipantFrom(e.target.value)} placeholder="dd/MM/yyyy" /></div>
                <div className="space-y-2"><Label>To Date</Label><Input value={participantTo} onChange={(e) => setParticipantTo(e.target.value)} placeholder="dd/MM/yyyy" /></div>
              </div>
              <Button onClick={handleParticipantList} disabled={participantLoading}>{participantLoading ? 'Fetching...' : 'List Participants'}</Button>
              <ResultBlock data={participantResult} />
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
