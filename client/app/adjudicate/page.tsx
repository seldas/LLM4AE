import { Suspense } from 'react';
import AdjudicateClient from './AdjudicateClient';

export const dynamic = 'force-dynamic';

export default function AdjudicatePage() {
  return (
    <Suspense fallback={<div className="p-6">Loading adjudication tool...</div>}>
      <AdjudicateClient />
    </Suspense>
  );
}
