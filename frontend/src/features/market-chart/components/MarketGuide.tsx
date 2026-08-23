const candleFields = [
  ["O · Open", "First traded price"],
  ["H · High", "Highest traded price"],
  ["L · Low", "Lowest traded price"],
  ["C · Close", "Latest or final price"],
  ["V · Volume", "Amount traded"],
] as const;

const connectionStates = [
  ["Live", "bg-pos", "Updates are arriving"],
  ["Stale", "bg-warn", "The last update is old"],
  ["Reconnecting", "bg-accent", "Restoring the data stream"],
  ["Error", "bg-neg", "Check the message or retry"],
] as const;

export function MarketGuide() {
  return (
    <aside
      aria-label="Beginner candle guide"
      className="min-h-0 overflow-hidden rounded-lg border border-line bg-surface xl:overflow-y-auto"
    >
      <header className="border-b border-subtle px-3 py-2.5">
        <h2 className="text-sm font-semibold tracking-tight text-ink">Chart guide</h2>
        <p className="mt-0.5 text-[11px] leading-4 text-faint">
          A quick reference while watching live candles.
        </p>
      </header>

      <section className="border-b border-subtle px-3 py-2.5" aria-labelledby="candle-update-title">
        <h3 id="candle-update-title" className="text-xs font-semibold text-ink">
          How candles update
        </h3>
        <div className="mt-2 space-y-2.5">
          <GuideRule
            label="Same open time"
            action="Update"
            description="The newest candle changes as trades arrive."
            variant="update"
          />
          <GuideRule
            label="New open time"
            action="Append"
            description="A new candle starts after the timeframe closes."
            variant="append"
          />
        </div>
      </section>

      <section className="border-b border-subtle px-3 py-2.5" aria-labelledby="read-candle-title">
        <h3 id="read-candle-title" className="text-xs font-semibold text-ink">
          Read a candle
        </h3>
        <p className="mt-1 text-[11px] leading-4 text-faint">
          Green closes above open; red closes below open.
        </p>
        <dl className="mt-2 grid grid-cols-2 gap-x-2 gap-y-1.5">
          {candleFields.map(([term, description]) => (
            <div key={term} className={term.startsWith("V") ? "col-span-2" : undefined}>
              <dt className="font-mono text-[10px] font-semibold text-dim">{term}</dt>
              <dd className="text-[10px] leading-4 text-faint">{description}</dd>
            </div>
          ))}
        </dl>
      </section>

      <section className="px-3 py-2.5" aria-labelledby="connection-state-title">
        <h3 id="connection-state-title" className="text-xs font-semibold text-ink">
          Connection states
        </h3>
        <ul className="mt-2 space-y-1.5">
          {connectionStates.map(([state, color, description]) => (
            <li key={state} className="grid grid-cols-[0.45rem_4.5rem_1fr] items-center gap-1.5">
              <span aria-hidden="true" className={`h-1.5 w-1.5 rounded-full ${color}`} />
              <span className="text-[10px] font-medium text-dim">{state}</span>
              <span className="text-[10px] leading-4 text-faint">{description}</span>
            </li>
          ))}
        </ul>
      </section>
    </aside>
  );
}

type GuideRuleProps = {
  label: string;
  action: string;
  description: string;
  variant: "update" | "append";
};

function GuideRule({ label, action, description, variant }: GuideRuleProps) {
  return (
    <div>
      <div className="flex items-center justify-between gap-2">
        <span className="text-[11px] font-medium text-dim">{label}</span>
        <span className="rounded border border-accent/30 bg-accent/10 px-1.5 py-0.5 font-mono text-[10px] font-semibold text-accent-soft">
          {action}
        </span>
      </div>
      <div className="my-1.5 flex h-5 items-center gap-1 rounded bg-workspace px-2" aria-hidden="true">
        <MiniCandle tone="pos" />
        <MiniCandle tone="neg" />
        <MiniCandle tone="pos" />
        <span className="mx-1 text-[10px] text-faint">→</span>
        <MiniCandle tone="pos" emphasized={variant === "update"} />
        {variant === "append" && <MiniCandle tone="pos" emphasized />}
      </div>
      <p className="text-[10px] leading-4 text-faint">{description}</p>
    </div>
  );
}

function MiniCandle({ tone, emphasized = false }: { tone: "pos" | "neg"; emphasized?: boolean }) {
  const body = tone === "pos" ? "bg-pos" : "bg-neg";
  return (
    <span
      className={`relative inline-flex h-4 w-2 items-center justify-center ${
        emphasized ? "rounded-sm ring-1 ring-accent" : ""
      }`}
    >
      <span className={`h-3 w-px ${body}`} />
      <span className={`absolute h-2 w-1.5 rounded-[1px] ${body}`} />
    </span>
  );
}
