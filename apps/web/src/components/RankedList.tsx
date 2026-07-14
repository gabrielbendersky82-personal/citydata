"use client";
import { ScoredNeighborhood } from "../lib/scoring/types";
import { ConfidenceBadge, confidenceLevel } from "./ConfidenceBadge";
import { ScoreBar } from "./ScoreBar";

export function RankedList({
  scored,
  onSelect,
  selectedId,
  compareIds,
  onToggleCompare,
}: {
  scored: ScoredNeighborhood[];
  onSelect: (id: number) => void;
  selectedId: number | null;
  compareIds: number[];
  onToggleCompare: (id: number) => void;
}) {
  const ranked = scored.filter((s) => s.rank != null);
  const excluded = scored.filter((s) => s.excluded);
  const sparse = scored.filter((s) => !s.excluded && s.insufficientData);

  return (
    <div className="h-full overflow-y-auto">
      <ol>
        {ranked.map((s) => (
          <li
            key={s.id}
            className="px-3 py-2 border-b cursor-pointer transition-colors"
            style={{
              borderColor: "var(--hairline)",
              background: s.id === selectedId ? "color-mix(in srgb, var(--accent) 10%, transparent)" : "transparent",
            }}
            onClick={() => onSelect(s.id)}
          >
            <div className="flex items-center gap-2">
              <span className="w-6 text-right text-xs tnum shrink-0" style={{ color: "var(--ink-muted)" }}>
                {s.rank}
              </span>
              <span className="flex-1 text-sm truncate" style={{ color: "var(--ink-1)" }}>{s.name}</span>
              <span className="text-sm tnum font-semibold" style={{ color: "var(--ink-1)" }}>
                {Math.round(s.score!)}
              </span>
              <input
                type="checkbox"
                checked={compareIds.includes(s.id)}
                onChange={() => onToggleCompare(s.id)}
                onClick={(e) => e.stopPropagation()}
                title="Compare"
                aria-label={`Compare ${s.name}`}
              />
            </div>
            <div className="flex items-center gap-2 mt-1 pl-8">
              <div className="flex-1">
                <ScoreBar value={s.score} />
              </div>
              <ConfidenceBadge level={confidenceLevel(s.confidence)} />
            </div>
          </li>
        ))}
      </ol>

      {sparse.length > 0 && (
        <Section title="Not enough data for your priorities">
          {sparse.map((s) => (
            <MutedRow key={s.id} name={s.name} note="sparse data" onClick={() => onSelect(s.id)} />
          ))}
        </Section>
      )}
      {excluded.length > 0 && (
        <Section title="Excluded by your hard limits">
          {excluded.map((s) => (
            <MutedRow key={s.id} name={s.name} note={s.exclusionReasons.join("; ")} onClick={() => onSelect(s.id)} />
          ))}
        </Section>
      )}
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mt-2">
      <h3 className="px-3 py-1 text-[11px] uppercase tracking-wide" style={{ color: "var(--ink-muted)" }}>
        {title}
      </h3>
      <ul>{children}</ul>
    </div>
  );
}

function MutedRow({ name, note, onClick }: { name: string; note: string; onClick: () => void }) {
  return (
    <li
      className="px-3 py-1.5 border-b cursor-pointer opacity-60 text-sm flex justify-between gap-2"
      style={{ borderColor: "var(--hairline)", color: "var(--ink-2)" }}
      onClick={onClick}
    >
      <span className="truncate">{name}</span>
      <span className="text-[11px] shrink-0 max-w-[50%] truncate" title={note}>{note}</span>
    </li>
  );
}
