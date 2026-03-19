import { Suspense } from 'react';
import AnnoToolClient from './AnnoToolClient';

export const dynamic = 'force-dynamic'; // Avoid static rendering errors

export default function AnnotatePage() {
  return (
    <Suspense fallback={<div className="p-6">Loading annotation tool...</div>}>
      <AnnoToolClient />
    </Suspense>
  );
}
