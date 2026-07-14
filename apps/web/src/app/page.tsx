import Link from "next/link";

const CITIES = [
  { slug: "chicago", name: "Chicago", state: "IL", live: true },
  { slug: "austin", name: "Austin", state: "TX", live: false },
  { slug: "seattle", name: "Seattle", state: "WA", live: false },
];

export default function Home() {
  return (
    <main className="min-h-dvh flex flex-col items-center justify-center gap-8 p-8">
      <div className="text-center max-w-lg">
        <h1 className="text-3xl font-bold mb-2" style={{ color: "var(--ink-1)" }}>
          Which neighborhood fits <em>you</em>?
        </h1>
        <p className="text-sm" style={{ color: "var(--ink-2)" }}>
          Pick a city, tell us what you care about — safety, rent, schools, walkability,
          transit, hazards, your own places — and get a transparent, explainable ranking
          of every neighborhood. No black boxes: every score shows its math.
        </p>
      </div>
      <div className="flex flex-wrap gap-3 justify-center">
        {CITIES.map((c) =>
          c.live ? (
            <Link
              key={c.slug}
              href={`/${c.slug}`}
              className="px-6 py-4 rounded-lg border text-lg font-semibold shadow-sm transition-transform hover:scale-105"
              style={{ borderColor: "var(--border)", background: "var(--surface-1)", color: "var(--ink-1)" }}
            >
              {c.name}, {c.state}
            </Link>
          ) : (
            <span
              key={c.slug}
              className="px-6 py-4 rounded-lg border text-lg opacity-50 cursor-not-allowed"
              style={{ borderColor: "var(--border)", color: "var(--ink-2)" }}
              title="Coming soon"
            >
              {c.name}, {c.state} <span className="text-xs">(soon)</span>
            </span>
          ),
        )}
      </div>
      <p className="text-xs max-w-md text-center" style={{ color: "var(--ink-muted)" }}>
        Decision support, not advice — data comes from public sources with gaps and lags.
        Always verify in person. <Link href="/data" className="underline">Sources & methodology</Link>
      </p>
    </main>
  );
}
