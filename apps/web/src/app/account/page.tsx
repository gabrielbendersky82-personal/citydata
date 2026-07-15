"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import type { Session } from "@supabase/supabase-js";
import { getSupabase, supabaseConfigured } from "../../lib/supabase/client";
import { useAppStore } from "../../lib/store";
import { Weights, Filter, Pin } from "../../lib/scoring/types";

interface SavedProfile {
  id: string;
  name: string;
  city_id: number | null;
  weights: Weights;
  filters: Filter[];
  pins: Pin[];
  created_at: string;
}

export default function AccountPage() {
  const supabase = getSupabase();
  const store = useAppStore();
  const [session, setSession] = useState<Session | null>(null);
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [profiles, setProfiles] = useState<SavedProfile[]>([]);
  const [name, setName] = useState("");
  const [status, setStatus] = useState<string | null>(null);

  useEffect(() => {
    if (!supabase) return;
    supabase.auth.getSession().then(({ data }) => setSession(data.session));
    const { data: sub } = supabase.auth.onAuthStateChange((_e, s) => setSession(s));
    return () => sub.subscription.unsubscribe();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!supabase || !session) return;
    supabase
      .from("weight_profiles")
      .select("*")
      .order("created_at", { ascending: false })
      .then(({ data }) => setProfiles((data as SavedProfile[]) ?? []));
  }, [supabase, session, status]);

  if (!supabaseConfigured) {
    return (
      <Shell>
        <p className="text-sm" style={{ color: "var(--ink-2)" }}>
          Accounts aren&apos;t configured on this deployment yet — everything else works without
          signing in, and you can share your setup via the Share button (it&apos;s all in the URL).
        </p>
      </Shell>
    );
  }

  if (!session) {
    return (
      <Shell>
        <p className="text-sm mb-3" style={{ color: "var(--ink-2)" }}>
          Sign in with a magic link to save weight profiles, pins, and shortlists.
        </p>
        <form
          className="flex gap-2"
          onSubmit={async (e) => {
            e.preventDefault();
            const { error } = await supabase!.auth.signInWithOtp({ email });
            if (!error) setSent(true);
          }}
        >
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            className="flex-1 rounded border px-2 py-1.5 text-sm bg-transparent"
            style={{ borderColor: "var(--border)", color: "var(--ink-1)" }}
          />
          <button type="submit" className="px-3 py-1.5 rounded text-sm text-white" style={{ background: "var(--accent)" }}>
            {sent ? "Sent — check email" : "Send link"}
          </button>
        </form>
      </Shell>
    );
  }

  async function saveCurrent() {
    if (!name.trim()) return;
    const { error } = await supabase!.from("weight_profiles").insert({
      user_id: session!.user.id,
      name: name.trim(),
      weights: store.weights,
      filters: store.filters,
      pins: store.pins,
    });
    setStatus(error ? `Save failed: ${error.message}` : "Saved");
    setName("");
  }

  return (
    <Shell>
      <div className="flex items-center justify-between mb-4">
        <p className="text-sm" style={{ color: "var(--ink-2)" }}>{session.user.email}</p>
        <button
          className="text-xs underline"
          style={{ color: "var(--ink-muted)" }}
          onClick={() => supabase!.auth.signOut()}
        >
          Sign out
        </button>
      </div>

      <div className="flex gap-2 mb-2">
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Name this setup (e.g. “Spring move”)"
          className="flex-1 rounded border px-2 py-1.5 text-sm bg-transparent"
          style={{ borderColor: "var(--border)", color: "var(--ink-1)" }}
        />
        <button onClick={saveCurrent} className="px-3 py-1.5 rounded text-sm text-white" style={{ background: "var(--accent)" }}>
          Save current setup
        </button>
      </div>
      {status && <p className="text-xs mb-2" style={{ color: "var(--ink-muted)" }}>{status}</p>}

      <ul className="divide-y" style={{ borderColor: "var(--hairline)" }}>
        {profiles.map((p) => (
          <li key={p.id} className="py-2 flex items-center justify-between gap-2 text-sm">
            <span style={{ color: "var(--ink-1)" }}>{p.name}</span>
            <span className="flex gap-3">
              <button
                className="underline"
                style={{ color: "var(--accent)" }}
                onClick={() => {
                  store.loadConfig({ w: p.weights, f: p.filters ?? [], p: p.pins ?? [] });
                  setStatus(`Loaded “${p.name}” — open a city to see it applied`);
                }}
              >
                Load
              </button>
              <button
                className="underline"
                style={{ color: "var(--ink-muted)" }}
                onClick={async () => {
                  await supabase!.from("weight_profiles").delete().eq("id", p.id);
                  setStatus("Deleted");
                }}
              >
                Delete
              </button>
            </span>
          </li>
        ))}
        {!profiles.length && (
          <li className="py-2 text-xs" style={{ color: "var(--ink-muted)" }}>No saved setups yet.</li>
        )}
      </ul>
    </Shell>
  );
}

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <main className="max-w-xl mx-auto p-8">
      <Link href="/" className="text-sm underline" style={{ color: "var(--accent)" }}>← citydata</Link>
      <h1 className="text-2xl font-bold mt-3 mb-4" style={{ color: "var(--ink-1)" }}>Your account</h1>
      {children}
    </main>
  );
}
