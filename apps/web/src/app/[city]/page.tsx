import { Suspense } from "react";
import { CityApp } from "./CityApp";

export default async function CityPage({ params }: { params: Promise<{ city: string }> }) {
  const { city } = await params;
  return (
    <Suspense>
      <CityApp city={city} />
    </Suspense>
  );
}
