import { useNavigate } from 'react-router';
import { Button } from '../components/ui/button';

export function NotFoundPage() {
  const navigate = useNavigate();
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-4 text-center">
      <p className="text-5xl font-bold text-muted-foreground">404</p>
      <p className="text-muted-foreground">That page doesn't exist.</p>
      <Button onClick={() => navigate('/')}>Back to dashboard</Button>
    </div>
  );
}
