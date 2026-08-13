import { useState } from 'react';
import { useNavigate } from 'react-router';
import { User, Lock, ShieldCheck } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { useAuth } from '../../contexts/AuthContext';

export function LoginPage() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username || !password) return toast.error('Enter username and password');
    setLoading(true);
    try {
      const ok = await login(username, password);
      if (ok) {
        toast.success('Login successful');
        navigate('/', { replace: true });
      } else {
        toast.error('Invalid username or password');
      }
    } catch {
      toast.error('Connection failed — check backend URL');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen">
      <div className="relative flex flex-1 items-center justify-center bg-white p-4 sm:p-8 dark:bg-gray-950">
        <div className="w-full max-w-md">
          <div className="mb-8 flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary text-lg font-bold text-primary-foreground">
              N
            </div>
            <span className="text-xl font-semibold tracking-tight">NHCX</span>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Sign In</CardTitle>
              <CardDescription>Enter your credentials to access the NHCX dashboard</CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="username">Username</Label>
                  <div className="relative">
                    <User className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                    <Input
                      id="username"
                      type="text"
                      placeholder="admin"
                      value={username}
                      onChange={(e) => setUsername(e.target.value)}
                      className="pl-10"
                      required
                      autoFocus
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="password">Password</Label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                    <Input
                      id="password"
                      type="password"
                      placeholder="Enter password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      className="pl-10"
                      required
                    />
                  </div>
                </div>
                <Button type="submit" className="w-full" disabled={loading}>
                  {loading ? 'Signing in...' : 'Sign In'}
                </Button>
              </form>
            </CardContent>
          </Card>

          <div className="mt-6 text-center text-sm text-gray-500">
            <p>NHCX — National Health Claims Exchange</p>
          </div>
        </div>
      </div>

      <div className="hidden flex-1 items-center justify-center bg-gradient-to-br from-cyan-600 to-cyan-500 p-8 lg:flex">
        <div className="max-w-lg space-y-6 text-white">
          <div className="rounded-2xl bg-white/10 p-8 backdrop-blur-sm">
            <ShieldCheck className="mb-4 h-16 w-16" />
            <h2 className="mb-4 text-3xl font-bold">NHCX Claims Exchange</h2>
            <p className="text-lg text-white/90">
              Digital health-insurance claims — eligibility, pre-auth, and claim
              settlement over the ABDM claims exchange.
            </p>
          </div>
          <div className="grid grid-cols-2 gap-4">
            {[
              { k: 'ABDM', k2: 'Compliant claims exchange' },
              { k: 'FHIR', k2: 'R4 standard bundles' },
              { k: 'JWE', k2: 'Encrypted payloads' },
              { k: '24/7', k2: 'Always-on availability' },
            ].map(({ k, k2 }) => (
              <div key={k} className="rounded-xl bg-white/10 p-4 backdrop-blur-sm">
                <div className="text-3xl font-bold">{k}</div>
                <div className="text-sm text-white/80">{k2}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
