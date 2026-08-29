import { ArrowRight, GitBranch, History, Trophy } from "lucide-react";
import { useStore, type Page } from "../../../lib/store";

// Plain-language guide rail shown beside the saved-strategies list (list mode).
// Mirrors the Market screen's Chart guide pattern: persistent orientation that
// fills the space with value instead of leaving it empty.
export function StrategiesGuide() {
  const { navigate } = useStore();

  const quickActions: { icon: typeof GitBranch; label: string; body: string; page: Page }[] = [
    {
      icon: GitBranch,
      label: "New strategy",
      body: "Start from a preset or describe one in your own words.",
      page: "strategyNew",
    },
    {
      icon: History,
      label: "Run a backtest",
      body: "Replay a strategy on history. No real trades are placed.",
      page: "backtests",
    },
    {
      icon: Trophy,
      label: "Compare on the leaderboard",
      body: "Rank candidates on a reproducible Top-K board.",
      page: "leaderboard",
    },
  ];

  const steps: { n: string; title: string; body: string }[] = [
    { n: "1", title: "Build or pick a strategy", body: "Choose a preset, or combine a few methods." },
    { n: "2", title: "Set the parameters", body: "Tune the settings, or keep the recommended ones." },
    { n: "3", title: "Backtest and compare", body: "Check history performance, then rank it." },
  ];

  return (
    <aside
      aria-label="Strategies guide"
      className="hidden min-h-0 w-[240px] shrink-0 overflow-hidden border-l border-line bg-surface xl:flex xl:flex-col xl:overflow-y-auto"
    >
      <header className="border-b border-subtle px-4 py-3">
        <h3 className="text-sm font-semibold tracking-tight text-ink">Start here</h3>
        <p className="mt-0.5 text-[11.5px] leading-4 text-faint">
          A quick guide to building and testing a strategy.
        </p>
      </header>

      {/* quick actions */}
      <section className="border-b border-subtle px-4 py-3">
        <h4 className="text-xs font-semibold text-ink">Quick actions</h4>
        <ul className="mt-2.5 space-y-1">
          {quickActions.map(({ icon: Icon, label, body, page }) => (
            <li key={page}>
              <button
                type="button"
                onClick={() => navigate(page)}
                className="group flex w-full items-start gap-3 rounded-[8px] px-2 py-2 text-left transition-colors hover:bg-surface-hover"
              >
                <Icon size={16} className="mt-0.5 shrink-0 text-faint group-hover:text-accent" />
                <span className="min-w-0">
                  <span className="flex items-center gap-1 text-[12px] font-medium text-ink">
                    {label}
                    <ArrowRight size={11} className="text-faint opacity-0 transition-opacity group-hover:opacity-100" />
                  </span>
                  <span className="mt-0.5 block text-[11px] leading-4 text-faint">{body}</span>
                </span>
              </button>
            </li>
          ))}
        </ul>
      </section>

      {/* getting started journey */}
      <section className="px-4 py-3">
        <h4 className="text-xs font-semibold text-ink">Getting started</h4>
        <ol className="mt-2.5 space-y-3">
          {steps.map((s) => (
            <li key={s.n} className="flex items-start gap-2.5">
              <span className="grid h-5 w-5 shrink-0 place-items-center rounded-[6px] bg-accent/15 font-mono text-[11px] font-semibold text-accent">
                {s.n}
              </span>
              <span className="min-w-0">
                <span className="block text-[11.5px] font-medium text-ink">{s.title}</span>
                <span className="mt-0.5 block text-[11px] leading-4 text-faint">{s.body}</span>
              </span>
            </li>
          ))}
        </ol>
      </section>
    </aside>
  );
}
