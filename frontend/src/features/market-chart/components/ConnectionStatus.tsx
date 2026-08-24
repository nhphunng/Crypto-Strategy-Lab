import {
  AlertTriangle,
  CheckCircle2,
  Clock3,
  LoaderCircle,
  RefreshCw,
} from "lucide-react";

import type { ConnectionState, MarketDataErrorPayload } from "../types";

export type ConnectionStatusProps = {
  slotId: string;
  connectionState: ConnectionState;
  lastEventAt?: string;
  attempt?: number;
  error?: MarketDataErrorPayload;
};

const STATUS = {
  LOADING: { label: "Loading", Icon: LoaderCircle, tone: "text-info" },
  LIVE: { label: "Live", Icon: CheckCircle2, tone: "text-pos" },
  STALE: { label: "Stale", Icon: Clock3, tone: "text-warn" },
  RECONNECTING: {
    label: "Reconnecting",
    Icon: RefreshCw,
    tone: "text-warn",
  },
  ERROR: { label: "Error", Icon: AlertTriangle, tone: "text-neg" },
  RELEASED: { label: "Released", Icon: Clock3, tone: "text-faint" },
} as const;

export function ConnectionStatus({
  slotId,
  connectionState,
  lastEventAt,
  attempt,
  error,
}: ConnectionStatusProps) {
  const metadata = STATUS[connectionState];
  return (
    <div
      id={`status-chart-${slotId}`}
      role="status"
      aria-live="polite"
      aria-atomic="true"
      className={`inline-flex min-h-7 flex-wrap items-center gap-1.5 text-xs font-medium ${metadata.tone}`}
    >
      <metadata.Icon
        data-status-icon
        aria-hidden="true"
        size={14}
        className={connectionState === "RECONNECTING" ? "csl-spin" : undefined}
      />
      <span>{metadata.label}</span>
      {(connectionState === "LIVE" ||
        connectionState === "STALE" ||
        connectionState === "RECONNECTING") &&
        lastEventAt !== undefined && (
          <span className="font-mono text-faint">· {lastEventAt}</span>
        )}
      {connectionState === "RECONNECTING" && attempt !== undefined && (
        <span className="font-mono text-faint">· attempt {attempt}</span>
      )}
      {connectionState === "ERROR" && error !== undefined && (
        <span className="font-normal text-dim">· {error.message}</span>
      )}
    </div>
  );
}
