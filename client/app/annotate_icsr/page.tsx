import { Suspense } from 'react';
import AnnotateIcsrClient from './AnnotateIcsrClient';

export const dynamic = 'force-dynamic';

export default function AnnotateIcsrPage() {
  return (
    <Suspense fallback={<div className="p-6">Loading ICSR annotation tool...</div>}>
      <AnnotateIcsrClient />
    </Suspense>
  );
}
