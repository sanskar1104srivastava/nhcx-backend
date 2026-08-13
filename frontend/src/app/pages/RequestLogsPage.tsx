import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import nhcxService, { LogEntry } from '../../services/nhcxService';
import { RefreshCw, ChevronDown, ChevronRight } from 'lucide-react';

export function RequestLogsPage() {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<Record<string, any> | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const data = await nhcxService.listLogs(200);
      setLogs(Array.isArray(data) ? data : []);
    } catch {
      setLogs([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchLogs(); }, []);

  const toggleExpand = async (apiCallId: string) => {
    if (expandedId === apiCallId) {
      setExpandedId(null);
      setDetail(null);
      return;
    }
    setExpandedId(apiCallId);
    setDetailLoading(true);
    try {
      const data = await nhcxService.getLog(apiCallId);
      setDetail(data as any);
    } catch {
      setDetail({ error: 'Failed to load detail' });
    } finally {
      setDetailLoading(false);
    }
  };

  const stateColor = (s: string) => {
    if (s === 'responded_complete') return 'bg-green-100 text-green-800';
    if (s === 'acked') return 'bg-blue-100 text-blue-800';
    if (s === 'error' || s === 'dead') return 'bg-red-100 text-red-800';
    if (s === 'initiated') return 'bg-amber-100 text-amber-800';
    return 'bg-gray-100 text-gray-800';
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Request Logs</h1>
          <p className="text-sm text-muted-foreground">All NHCX requests and their current state</p>
        </div>
        <Button variant="outline" onClick={fetchLogs} disabled={loading}>
          <RefreshCw className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      <Card>
        <CardContent className="p-0">
          {loading ? (
            <div className="p-6 text-sm text-muted-foreground">Loading...</div>
          ) : logs.length === 0 ? (
            <div className="p-6 text-sm text-muted-foreground">No logs found.</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead><tr className="border-b bg-muted/50 text-left">
                  <th className="p-3 w-8"></th>
                  <th className="p-3 font-medium">Time</th>
                  <th className="p-3 font-medium">Use Case</th>
                  <th className="p-3 font-medium">State</th>
                  <th className="p-3 font-medium">Direction</th>
                  <th className="p-3 font-medium">API Call ID</th>
                  <th className="p-3 font-medium">Correlation ID</th>
                </tr></thead>
                <tbody>
                  {logs.map((log) => (
                    <>
                      <tr key={log.apiCallId} className="border-b cursor-pointer hover:bg-muted/30" onClick={() => toggleExpand(log.apiCallId)}>
                        <td className="p-3">{expandedId === log.apiCallId ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}</td>
                        <td className="p-3 text-muted-foreground whitespace-nowrap">{log.createdAt || '-'}</td>
                        <td className="p-3 font-medium">{log.useCase || '-'}</td>
                        <td className="p-3"><Badge variant="secondary" className={stateColor(log.state)}>{log.state}</Badge></td>
                        <td className="p-3 text-muted-foreground">{log.direction || '-'}</td>
                        <td className="p-3 font-mono text-xs">{log.apiCallId?.slice(0, 12)}...</td>
                        <td className="p-3 font-mono text-xs">{log.correlationId?.slice(0, 12)}...</td>
                      </tr>
                      {expandedId === log.apiCallId && (
                        <tr key={`${log.apiCallId}-detail`}>
                          <td colSpan={7} className="bg-muted/20 p-4">
                            {detailLoading ? (
                              <p className="text-sm text-muted-foreground">Loading detail...</p>
                            ) : detail ? (
                              <div className="space-y-3">
                                <div className="grid gap-4 sm:grid-cols-2 text-sm">
                                  <div><span className="font-medium">State:</span> {detail.state}</div>
                                  <div><span className="font-medium">Use Case:</span> {detail.useCase}</div>
                                  <div><span className="font-medium">Sender:</span> {detail.senderCode}</div>
                                  <div><span className="font-medium">Recipient:</span> {detail.recipientCode}</div>
                                </div>
                                {detail.fhirBundleIn && (
                                  <div>
                                    <p className="text-sm font-medium mb-1">Inbound FHIR Bundle:</p>
                                    <pre className="overflow-x-auto rounded bg-muted p-3 text-xs max-h-48 overflow-y-auto">
                                      {typeof detail.fhirBundleIn === 'string' ? detail.fhirBundleIn : JSON.stringify(detail.fhirBundleIn, null, 2)}
                                    </pre>
                                  </div>
                                )}
                                {detail.fhirBundleOut && (
                                  <div>
                                    <p className="text-sm font-medium mb-1">Outbound FHIR Bundle:</p>
                                    <pre className="overflow-x-auto rounded bg-muted p-3 text-xs max-h-48 overflow-y-auto">
                                      {typeof detail.fhirBundleOut === 'string' ? detail.fhirBundleOut : JSON.stringify(detail.fhirBundleOut, null, 2)}
                                    </pre>
                                  </div>
                                )}
                              </div>
                            ) : null}
                          </td>
                        </tr>
                      )}
                    </>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
