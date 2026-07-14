import { Suspense } from "react";
import { CompareView } from "./CompareView";

export default async function ComparePage({ params }: { params: Promise<{ city: string }> }) {
  const { city } = await params;
  return (
    <Suspense>
      <CompareView city={city} />
    </Suspense>
  );
}
