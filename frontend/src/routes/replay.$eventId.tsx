import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { motion } from "motion/react";
import { ArrowLeft, CheckCircle2, FlaskConical, Target } from "lucide-react";
import { Button } from "@/components/ui/button";
import { APP_DATA_MODE, replayEventQuery } from "@/features/data/queries";
import { TopBar } from "@/features/shared/AppShell";
import { DataStatus } from "@/features/shared/DataStatus";
import { routeHead } from "@/features/shared/RouteMeta";
export const Route = createFileRoute("/replay/$eventId")({
  head: () =>
    routeHead(
      "Replay Case",
      "Inspect one verified Synoptiq forecast against the naive average, default model, and observed truth.",
    ),
  component: Page,
});
function Page() {
  const { eventId } = Route.useParams();
  const replay = useQuery(replayEventQuery(eventId));
  if (replay.isPending) {
    return (
      <>
        <TopBar mode={APP_DATA_MODE} />
        <div className="page-state">Loading replay case…</div>
      </>
    );
  }
  if (replay.isError || !replay.data) {
    return (
      <>
        <TopBar mode={APP_DATA_MODE} />
        <div className="page-state" role="alert">
          <h2>Replay case unavailable</h2>
          <p>
            {replay.error instanceof Error
              ? replay.error.message
              : "No replay case data was returned."}
          </p>
          <Button onClick={() => void replay.refetch()}>Retry</Button>
          <Link to="/replay">Back to replay cases</Link>
        </div>
      </>
    );
  }
  const d = replay.data;
  const miss = d.synoptiq_error > d.single_model_error;
  const vals = [
    { name: "Naive average", value: d.naive_average, error: d.naive_average_error },
    {
      name: `Single · ${d.single_model_choice.model}`,
      value: d.single_model_choice.forecast_value,
      error: d.single_model_error,
    },
    { name: "Synoptiq", value: d.synoptiq_blend, error: d.synoptiq_error },
  ];
  const min = Math.min(...vals.map((v) => v.value), d.reference_value) * 0.9,
    max = Math.max(...vals.map((v) => v.value), d.reference_value) * 1.07;
  return (
    <>
      <TopBar mode={APP_DATA_MODE} />
      <div className="page replay-detail">
        <div className="back-row">
          <Link to="/replay">
            <ArrowLeft />
            All cases
          </Link>
          <DataStatus mode={APP_DATA_MODE} />
        </div>
        <header className={`replay-hero ${miss ? "honest" : "win"}`}>
          <span className="kicker">
            {d.event_id} · +{d.lead_hours}H
          </span>
          <h1>{d.label}</h1>
          <p>{d.headline}</p>
          <div className="verdict">
            {miss ? <FlaskConical /> : <CheckCircle2 />}
            {miss ? "Scientifically honest miss" : "Contextual blend win"}
          </div>
        </header>
        <section className="race-panel panel">
          <div className="truth-head">
            <Target />
            <span>VERIFIED TRUTH</span>
            <strong>
              {d.reference_value.toFixed(1)} {d.unit}
            </strong>
          </div>
          <div className="race-track">
            <div
              className="truth-line"
              style={{ left: `${((d.reference_value - min) / (max - min)) * 100}%` }}
            />
            {vals.map((v, i) => (
              <div className="race-row" key={v.name}>
                <span>{v.name}</span>
                <div className="race-line">
                  <motion.i
                    initial={{ width: 0 }}
                    animate={{ width: `${((v.value - min) / (max - min)) * 100}%` }}
                    transition={{ duration: 1, delay: i * 0.35, ease: "easeOut" }}
                  />
                  <b style={{ left: `${((v.value - min) / (max - min)) * 100}%` }}>
                    {v.value.toFixed(1)}
                  </b>
                </div>
                <strong className={v.name === "Synoptiq" ? "accent" : ""}>
                  {v.error.toFixed(1)} error
                </strong>
              </div>
            ))}
          </div>
          <div className="raw-sources">
            {d.raw_sources.map((s) => (
              <span key={s.model}>
                <b>{s.model}</b>
                {s.forecast_value.toFixed(1)} {d.unit}
              </span>
            ))}
          </div>
        </section>
        <section className="commentary">
          <span className="kicker">MISSION COMMENTARY</span>
          {d.narrative.map((n, i) => (
            <motion.div
              key={n}
              initial={{ opacity: 0, x: -20 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true, amount: 0.6 }}
              transition={{ delay: i * 0.08 }}
            >
              <b>{String(i + 1).padStart(2, "0")}</b>
              <p>{n}</p>
            </motion.div>
          ))}
        </section>
      </div>
    </>
  );
}
