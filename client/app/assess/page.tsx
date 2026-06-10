import { Suspense } from 'react';
import AssessClient from './AssessClient';

export const dynamic = 'force-dynamic';

export default function AssessPage() {
  return (
    <Suspense fallback={<div className="p-6">Loading assess view...</div>}>
      <AssessClient />
    </Suspense>
  );
}

