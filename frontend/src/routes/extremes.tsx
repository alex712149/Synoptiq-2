import { createFileRoute } from "@tanstack/react-router";
import { useQuery, useSuspenseQuery } from "@tanstack/react-query";
import { z } from "zod";
import { zodValidator } from "@tanstack/zod-adapter";
import { CloudRain, Flame, Wind, ShieldCheck, ShieldQuestion } from "lucide-react";
import { APP_DATA_MODE, extremesQuery, leadTimesQuery, systemStatusQuery } from "@/features/data/queries";
import type { RegionCode } from "@/features/data/types";
import { SelectControl } from "@/features/shared/Controls";
import { SectionHeading } from "@/features/shared/SectionHeading";
import { TopBar } from "@/features/shared/AppShell";
import { routeHead } from "@/features/shared/RouteMeta";
const schema = z.object({
  region: z.enum(["KWG", "BOB", "IGP"]).catch("BOB"),
  lead: z.coerce.number().catch(72),
});
export const Route = createFileRoute("/extremes")({
  validateSearch: zodValidator(schema),
  head: () =>
    routeHead(
      "Extreme Weather Guidance",
      "View calibrated heavy-rain, heat, and high-wind exceedance probabilities from Synoptiq.",
    ),
  component: Page,
});
const icons = { precipitation: CloudRain, temperature: Flame, wind_speed: Wind };
const formatProbability = (value: number) =>
  value > 0 && value < 0.005 ? "<1%" : `${Math.round(value * 100)}%`;
function Page() {
  const s = Route.useSearch(),
    nav = Route.useNavigate();
  const { data: leads } = useSuspenseQuery(leadTimesQuery);
  const { data: systemStatus } = useSuspenseQuery(systemStatusQuery);
  const { data: r } = useQuery({
    ...extremesQuery(s.region, s.lead),
    enabled: APP_DATA_MODE === "mock" || systemStatus.ready,
  });
  const guidance = Array.isArray(r?.guidance) ? r.guidance : [];
  const liveUnavailable = APP_DATA_MODE === "live" && !systemStatus.ready;
  const set = (p: Partial<typeof s>) => nav({ to: ".", search: (q) => ({ ...q, ...p }) });
  return (
    <>
      <TopBar mode={APP_DATA_MODE} />
      <div className="page">
        <SectionHeading
          eyebrow="Threshold exceedance intelligence"
          title="Extreme weather guidance"
          copy="Compare real forecast values with hazard thresholds; show calibrated probability only when the matching model artifact is available."
        />
        <div className="control-deck compact">
          <SelectControl
            label="Region"
            value={s.region}
            onChange={(v) => set({ region: v as RegionCode })}
            options={["KWG", "BOB", "IGP"].map((v) => ({ value: v, label: v }))}
          />
          <SelectControl
            label="Lead time"
            value={String(s.lead)}
            onChange={(v) => set({ lead: Number(v) })}
            options={leads.map((v) => ({ value: String(v), label: `+${v} hours` }))}
          />
        </div>
        {liveUnavailable ? (
          <div className="page-state" role="status">
            <h2>REAL INPUTS UNAVAILABLE</h2>
            <p>Extreme guidance is withheld until current real provider inputs pass validation.</p>
          </div>
        ) : (
        <div className="threat-grid">
          {guidance.length === 0 ? (
            <div className="page-state">
              No extreme-weather guidance is available for this selection.
            </div>
          ) : (
            guidance.map((g) => {
              const Icon = icons[g.variable],
                pct = g.probability == null ? null : Math.round(g.probability * 100),
                level = pct == null ? "low" : pct >= 65 ? "high" : pct >= 35 ? "medium" : "low";
              return (
                <section className={`threat panel ${level}`} key={g.variable}>
                  <div className="threat-icon">
                    <Icon />
                  </div>
                  <span className="kicker">{g.variable.replace("_", " ")}</span>
                  <h2>{g.calibrated && g.probability != null ? formatProbability(g.probability) : "PROBABILITY UNAVAILABLE"}</h2>
                  <p>
                    Forecast: {g.forecast_value.toFixed(1)} {g.unit} · Threshold: {g.threshold} {g.unit}
                  </p>
                  <p>Threshold exceedance: {g.threshold_exceeded ? "YES" : "NO"}</p>
                  {g.calibrated && g.probability != null && (
                    <div className="threat-gauge">
                      <i style={{ transform: `rotate(${g.probability * 180 - 90}deg)` }} />
                    </div>
                  )}
                  <div className={`calibration ${g.calibrated ? "yes" : "no"}`}>
                    {g.calibrated ? <ShieldCheck /> : <ShieldQuestion />}
                    {g.calibrated ? "CALIBRATED · REAL MODEL" : "CALIBRATION NOT AVAILABLE"}
                  </div>
                </section>
              );
            })
          )}
        </div>
        )}
        {!liveUnavailable && guidance.length > 0 && (
          <div className="guidance-note">
            <ShieldQuestion />
            <div>
              <b>Probability is not certainty.</b>
              <p>
                Calibrated probability is shown only when available; otherwise guidance is limited
                to the forecast value and threshold comparison.
              </p>
            </div>
          </div>
        )}
      </div>
    </>
  );
}
