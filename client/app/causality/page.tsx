import { Suspense } from 'react';
import CausalityClient from './CausalityClient';

export const dynamic = 'force-dynamic';

export default function CausalityPage() {
  return (
    <Suspense fallback={<div className="p-6">Loading causality tool...</div>}>
      <CausalityClient />
    </Suspense>
  );
}
