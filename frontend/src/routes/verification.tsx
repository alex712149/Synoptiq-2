import { createFileRoute } from "@tanstack/react-router";
import { useSuspenseQuery } from "@tanstack/react-query";
import { CheckCircle2, Minus, TrendingDown, TrendingUp } from "lucide-react";
import { APP_DATA_MODE, verificationQuery } from "@/features/data/queries";
import { SectionHeading } from "@/features/shared/SectionHeading";
import { TopBar } from "@/features/shared/AppShell";
import { DataStatus } from "@/features/shared/DataStatus";
import { routeHead } from "@/features/shared/RouteMeta";

export const Route = createFileRoute("/verification")({
  head: () =>
    routeHead(
      "Verification Scorecard",
      "Review held-out Synoptiq performance across the pilot regions and forecast variables.",
    ),
  component: Page,
});

function Page() {
  const { data } = useSuspenseQuery(verificationQuery);
  const rows = Array.isArray(data) ? data : [];
  const mode = APP_DATA_MODE;
  const regions = ["KWG", "BOB", "IGP"] as const;
  const variables = ["precipitation", "temperature", "wind_speed"] as const;
  const strongest = [...rows].sort((a, b) => b.relative_improvement - a.relative_improvement)[0];
  const weakest = [...rows].sort((a, b) => a.relative_improvement - b.relative_improvement)[0];

  if (!rows.length)
    return (
      <>
        <TopBar mode={mode} />
        <div className="page-state">
          No held-out verification results are available yet. Run the real-data training and
          evaluation pipeline first.
        </div>
      </>
    );

  return (
    <>
      <TopBar mode={mode} />
      <div className="page">
        <SectionHeading
          eyebrow={
            mode === "live"
              ? "PROTOTYPE VALIDATION · 2025-02-26 to 2025-03-10"
              : "DEMO VALIDATION"
          }
          title="The complete scorecard"
          copy="Each cell uses the metric appropriate to that variable: CSI for heavy rainfall and RMSE for temperature and wind."
          action={<DataStatus mode={mode} />}
        />

        <div className="proof-strip">
          <div>
            <TrendingUp />
            <span>STRONGEST RESULT</span>
            <strong>
              {strongest
                ? `${strongest.relative_improvement >= 0 ? "+" : ""}${(strongest.relative_improvement * 100).toFixed(1)}%`
                : "—"}
            </strong>
            <small>{strongest ? `${strongest.region} · ${strongest.variable}` : "—"}</small>
          </div>
          <div>
            <CheckCircle2 />
            <span>PRECIPITATION TARGET</span>
            <strong>+5.0%</strong>
            <small>relative CSI target where applicable</small>
          </div>
          <div>
            <TrendingDown />
            <span>LOWEST RESULT</span>
            <strong>
              {weakest
                ? `${weakest.relative_improvement >= 0 ? "+" : ""}${(weakest.relative_improvement * 100).toFixed(1)}%`
                : "—"}
            </strong>
            <small>{weakest ? `${weakest.region} · ${weakest.variable}` : "—"}</small>
          </div>
        </div>

        <section className="matrix-panel panel">
          <div className="panel-head">
            <div>
              <span className="kicker">VARIABLE-APPROPRIATE METRICS</span>
              <h2>Region × variable matrix</h2>
            </div>
            <div className="matrix-key">
              <span className="negative">BELOW BASELINE</span>
              <span>NEUTRAL</span>
              <span className="positive">IMPROVEMENT</span>
            </div>
          </div>

          <div className="score-matrix">
            <div />
            {variables.map((v) => (
              <div className="matrix-col" key={v}>
                {v.replace("_", " ")}
              </div>
            ))}
            {regions.map((region) => (
              <div className="matrix-row-group" key={region}>
                <div className="matrix-region">{region}</div>
                {variables.map((variable) => {
                  const row = rows.find((r) => r.region === region && r.variable === variable);
                  if (!row)
                    return (
                      <div className="score-cell empty" key={variable}>
                        —
                      </div>
                    );
                  const tone =
                    row.relative_improvement < 0
                      ? "negative"
                      : row.meets_target === true
                        ? "positive"
                        : "neutral";
                  return (
                    <div className={`score-cell ${tone}`} key={variable}>
                      <div>
                        {row.relative_improvement >= 0 ? <TrendingUp /> : <TrendingDown />}
                        <strong>
                          {row.relative_improvement >= 0 ? "+" : ""}
                          {(row.relative_improvement * 100).toFixed(1)}%
                        </strong>
                      </div>
                      <span>
                        {row.metric}: Synoptiq {row.synoptiq_score.toFixed(3)}
                      </span>
                      <span>
                        {row.best_single_model} {row.best_single_model_score.toFixed(3)}
                      </span>
                      <small>
                        {row.meets_target == null
                          ? "BENCHMARK"
                          : row.meets_target
                            ? "TARGET MET"
                            : "TARGET NOT MET"}
                      </small>
                    </div>
                  );
                })}
              </div>
            ))}
          </div>

          <div className="target-note">
            <Minus />
            <span>
              CSI@50mm is the rainfall event metric; temperature and wind are evaluated with
              held-out RMSE so the scorecard does not misuse rainfall-specific metrics.
            </span>
          </div>
        </section>
      </div>
    </>
  );
}
