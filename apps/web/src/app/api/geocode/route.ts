import { NextRequest, NextResponse } from "next/server";

/**
 * Geocoding proxy: US Census Geocoder (free, no key, results storable).
 * Also accepts raw "lat, lon" input directly — handy for power users and
 * for environments where the geocoder is unreachable.
 */
const CENSUS_URL = "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress";

// simple per-instance cache; Supabase geocode_cache takes over post-provisioning
const cache = new Map<string, { lon: number; lat: number; matched: string }>();

export async function POST(req: NextRequest) {
  let address: unknown;
  try {
    ({ address } = await req.json());
  } catch {
    return NextResponse.json({ error: "invalid request" }, { status: 400 });
  }
  if (typeof address !== "string" || !address.trim() || address.length > 300) {
    return NextResponse.json({ error: "address required" }, { status: 400 });
  }
  const norm = address.trim().toLowerCase().replace(/\s+/g, " ");

  // "41.88, -87.63" style input
  const coords = norm.match(/^(-?\d{1,3}(?:\.\d+)?)[ ,]+(-?\d{1,3}(?:\.\d+)?)$/);
  if (coords) {
    const [a, b] = [Number(coords[1]), Number(coords[2])];
    // lat,lon (US: lat 18..72, lon -180..-65)
    const [lat, lon] = Math.abs(a) <= 90 && b < 0 ? [a, b] : [b, a];
    if (Math.abs(lat) <= 90 && Math.abs(lon) <= 180) {
      return NextResponse.json({ lon, lat, matched: `${lat}, ${lon}` });
    }
  }

  const hit = cache.get(norm);
  if (hit) return NextResponse.json({ lon: hit.lon, lat: hit.lat, matched: hit.matched });

  try {
    const url = `${CENSUS_URL}?address=${encodeURIComponent(address)}&benchmark=Public_AR_Current&format=json`;
    const r = await fetch(url, {
      headers: { "User-Agent": "citydata/0.1 (neighborhood fit app)" },
      signal: AbortSignal.timeout(10_000),
    });
    if (!r.ok) throw new Error(`census geocoder ${r.status}`);
    const data = await r.json();
    const match = data?.result?.addressMatches?.[0];
    if (!match) {
      return NextResponse.json({ error: "Address not found — include city and state." }, { status: 404 });
    }
    const out = {
      lon: match.coordinates.x as number,
      lat: match.coordinates.y as number,
      matched: match.matchedAddress as string,
    };
    cache.set(norm, out);
    return NextResponse.json(out);
  } catch {
    return NextResponse.json(
      { error: "Geocoder unavailable — try again, or enter coordinates as \"lat, lon\"." },
      { status: 502 },
    );
  }
}
