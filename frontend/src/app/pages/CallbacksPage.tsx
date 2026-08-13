import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { RefreshCw, ChevronDown, ChevronRight, ArrowDownLeft } from 'lucide-react';
import nhcxService, { LogEntry } from '../../services/nhcxService';

export function CallbacksPage() {
  const [callbacks, setCallbacks] = useState<LogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<Record<string, any> | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const fetchCallbacks = async () => {
    setLoading(true);
    try {
      const data = await nhcxService.listLogs(200);
      const all = Array.isArray(data) ? data : [];
      // Filter to only inbound (callbacks from NHCX/payers)
      setCallbacks(all.filter((l) => l.direction === 'inbound'));
    } catch {
      setCallbacks([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchCallbacks(); }, []);

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
    if (s === 'responded_partial') return 'bg-blue-100 text-blue-800';
    if (s === 'error' || s === 'dead') return 'bg-red-100 text-red-800';
    return 'bg-gray-100 text-gray-800';
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Callbacks</h1>
          <p className="text-sm text-muted-foreground">
            Inbound NHCX responses — coverage eligibility, preauth/claim decisions, payment notices
          </p>
        </div>
        <Button variant="outline" onClick={fetchCallbacks} disabled={loading}>
          <RefreshCw className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      <Card>
        <CardContent className="p-0">
          {loading ? (
            <div className="p-6 text-sm text-muted-foreground">Loading...</div>
          ) : callbacks.length === 0 ? (
            <div className="p-6 text-center">
              <ArrowDownLeft className="mx-auto h-8 w-8 text-muted-foreground/50 mb-2" />
              <p className="text-sm text-muted-foreground">
                No callbacks received yet. Callbacks appear here when NHCX or payers respond to your requests.
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead><tr className="border-b bg-muted/50 text-left">
                  <th className="p-3 w-8"></th>
                  <th className="p-3 font-medium">Time</th>
                  <th className="p-3 font-medium">Use Case</th>
                  <th className="p-3 font-medium">State</th>
                  <th className="p-3 font-medium">From (Sender)</th>
                  <th className="p-3 font-medium">Correlation ID</th>
                </tr></thead>
                <tbody>
                  {callbacks.map((log) => (
                    <>
                      <tr key={log.apiCallId} className="border-b cursor-pointer hover:bg-muted/30" onClick={() => toggleExpand(log.apiCallId)}>
                        <td className="p-3">{expandedId === log.apiCallId ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}</td>
                        <td className="p-3 text-muted-foreground whitespace-nowrap">{log.createdAt || '-'}</td>
                        <td className="p-3 font-medium">{log.useCase || '-'}</td>
                        <td className="p-3"><Badge variant="secondary" className={stateColor(log.state)}>{log.state}</Badge></td>
                        <td className="p-3 font-mono text-xs">{log.senderCode || '-'}</td>
                        <td className="p-3 font-mono text-xs">{log.correlationId?.slice(0, 16)}...</td>
                      </tr>
                      {expandedId === log.apiCallId && (
                        <tr key={`${log.apiCallId}-detail`}>
                          <td colSpan={6} className="bg-muted/20 p-4">
                            {detailLoading ? (
                              <p className="text-sm text-muted-foreground">Loading detail...</p>
                            ) : detail ? (
                              <div className="space-y-3">
                                <div className="grid gap-4 sm:grid-cols-2 text-sm">
                                  <div><span className="font-medium">API Call ID:</span> <span className="font-mono text-xs">{detail.apiCallId}</span></div>
                                  <div><span className="font-medium">Workflow ID:</span> {detail.workflowId}</div>
                                  <div><span className="font-medium">Status:</span> {detail.xHcxStatus || detail.state}</div>
                                  <div><span className="font-medium">Error:</span> {detail.errorCode || 'none'}</div>
                                </div>
                                {detail.fhirBundleIn && (
                                  <div>
                                    <p className="text-sm font-medium mb-1">Inbound FHIR Bundle:</p>
                                    <pre className="overflow-x-auto rounded bg-muted p-3 text-xs max-h-48 overflow-y-auto">
                                      {typeof detail.fhirBundleIn === 'string'
                                        ? (() => { try { return JSON.stringify(JSON.parse(detail.fhirBundleIn), null, 2); } catch { return detail.fhirBundleIn; } })()
                                        : JSON.stringify(detail.fhirBundleIn, null, 2)}
                                    </pre>
                                  </div>
                                )}
                                {!detail.fhirBundleIn && detail.largePayloadS3Key && (
                                  <div className="text-sm text-muted-foreground">
                                    FHIR bundle stored in S3 (key: {detail.largePayloadS3Key})
                                  </div>
                                )}
                                {!detail.fhirBundleIn && !detail.largePayloadS3Key && (
                                  <div className="text-sm text-muted-foreground">
                                    No FHIR bundle in this callback record
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
