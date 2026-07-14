"use client";
import useSWR from "swr";
import { Bundle } from "./scoring/types";

const fetcher = (url: string) =>
  fetch(url).then((r) => {
    if (!r.ok) throw new Error(`bundle fetch failed: ${r.status}`);
    return r.json();
  });

/** City bundles are static, versioned artifacts — cache immutably per session. */
export function useBundle(city: string) {
  return useSWR<Bundle>(`/bundles/${city}.json`, fetcher, {
    revalidateOnFocus: false,
    revalidateIfStale: false,
  });
}
