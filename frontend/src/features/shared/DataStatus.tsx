import { AlertTriangle, CloudCog } from "lucide-react";
export function DataStatus({
  mode,
  compact = false,
}: {
  mode: "live" | "mock";
  compact?: boolean;
}) {
  return (
    <div
      className={`status-pill ${mode === "live" ? "status-live" : "status-mock"}`}
      title={
        mode === "live"
          ? "Real prototype data; request availability is shown by each page"
          : "Using synthetic fixtures in explicit DEMO mode"
      }
    >
      {mode === "live" ? <CloudCog /> : <AlertTriangle />}
      <span>
        {compact
          ? mode === "live"
            ? "Real"
            : "Demo"
          : mode === "live"
            ? "Real prototype · limited history"
            : "Demo mode · synthetic data"}
      </span>
    </div>
  );
}
