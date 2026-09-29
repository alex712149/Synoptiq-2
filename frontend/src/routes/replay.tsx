import { createFileRoute, Link, Outlet, useRouterState } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight, CheckCircle2, FlaskConical } from "lucide-react";
import { APP_DATA_MODE, replayEventsQuery } from "@/features/data/queries";
import { SectionHeading } from "@/features/shared/SectionHeading";
import { TopBar } from "@/features/shared/AppShell";
import { DataStatus } from "@/features/shared/DataStatus";
import { routeHead } from "@/features/shared/RouteMeta";
import { Button } from "@/components/ui/button";
export const Route = createFileRoute("/replay")({
  head: () =>
    routeHead(
      "Counterfactual Bust Replay",
      "Replay verified Synoptiq forecast cases, including clear wins and scientifically honest misses.",
    ),
  component: Page,
});
function Page() {
  const isDetailRoute = useRouterState({
    select: (state) => state.location.pathname.startsWith("/replay/"),
  });
  return isDetailRoute ? <Outlet /> : <ReplayListPage />;
}

function ReplayListPage() {
  const query = useQuery(replayEventsQuery);
  const { data } = query;
  const rows = Array.isArray(data) ? data : [];
  if (query.isPending || query.isError) {
    return (
      <>
        <TopBar mode={APP_DATA_MODE} />
        <div className="page-state" role={query.isError ? "alert" : "status"}>
          <h2>{query.isError ? "REPLAY DATA UNAVAILABLE" : "LOADING REPLAY CASES"}</h2>
          <p>
            {query.isError
              ? query.error instanceof Error
                ? query.error.message
                : "The real replay API could not be reached."
              : "Loading verified historical replay cases from the real API."}
          </p>
          {query.isError && <Button onClick={() => void query.refetch()}>Retry</Button>}
        </div>
      </>
    );
  }
  return (
    <>
      <TopBar mode={APP_DATA_MODE} />
      <div className="page">
        <SectionHeading
          eyebrow={APP_DATA_MODE === "live" ? "REPLAY · HISTORICAL REAL DATA" : "DEMO REPLAY"}
          title="Counterfactual bust replay"
          copy="No selective storytelling. Every case is compared with the same baselines and the verified truth."
          action={<DataStatus mode={APP_DATA_MODE} />}
        />
        <div className="replay-list">
          {rows.length === 0 ? (
            <div className="page-state">
              No replay cases are available from the selected data source.
            </div>
          ) : (
            rows.map((e, i) => {
              const miss = e.headline.includes("not the single best");
              return (
                <Link
                  key={e.event_id}
                  to="/replay/$eventId"
                  params={{ eventId: e.event_id }}
                  className={`replay-card ${miss ? "honest" : "win"}`}
                >
                  <div className="case-index">0{i + 1}</div>
                  <div>
                    <span className="kicker">
                      {e.region} / {e.variable.replace("_", " ")}
                    </span>
                    <h2>{e.label}</h2>
                    <p>{e.headline}</p>
                  </div>
                  <div className="case-flavor">
                    {miss ? (
                      <>
                        <FlaskConical />
                        HONEST MISS
                      </>
                    ) : (
                      <>
                        <CheckCircle2 />
                        CLEAR WIN
                      </>
                    )}
                  </div>
                  <ArrowRight className="case-arrow" />
                </Link>
              );
            })
          )}
        </div>
      </div>
    </>
  );
}
