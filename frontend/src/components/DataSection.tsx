import { useEffect, useState } from "react";
import { api, ApiError } from "../api/client";
import type { DatasetResponse, TableInfo } from "../api/types";
import { SnacksChart } from "./SnacksChart";

/** Monthly averages: the table view of the chart. */
function monthlyAverages(data: DatasetResponse) {
  const groups = new Map<string, number[]>();
  data.series.forEach((p) => {
    const key = p.date.slice(0, 7);
    groups.set(key, [...(groups.get(key) ?? []), p.units]);
  });
  return [...groups].map(([month, units]) => ({
    month: new Date(`${month}-01T00:00:00`).toLocaleDateString("en-GB", { month: "short", year: "numeric" }),
    avg: Math.round(units.reduce((a, b) => a + b, 0) / units.length),
  }));
}

export function DataSection({ tables }: { tables: TableInfo[] }) {
  const [data, setData] = useState<DatasetResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [asTable, setAsTable] = useState(false);

  useEffect(() => {
    api
      .dataset()
      .then(setData)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Couldn't load the data."));
  }, []);

  return (
    <>
      <div className="demo">
        <div className="demo-title-row">
          <div className="demo-title">⚡ The real data · {data?.category ?? "Snacks"} units per day</div>
          {data && (
            <div className="tabs" role="tablist">
              <button role="tab" aria-selected={!asTable} className={!asTable ? "active" : ""} onClick={() => setAsTable(false)}>
                Chart
              </button>
              <button role="tab" aria-selected={asTable} className={asTable ? "active" : ""} onClick={() => setAsTable(true)}>
                Table
              </button>
            </div>
          )}
        </div>
        {error && <p className="bad">{error}</p>}
        {!data && !error && <div className="thinking" aria-label="Loading" />}
        {data && !asTable && <SnacksChart data={data} />}
        {data && asTable && (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Month</th>
                  <th>Avg units / day</th>
                </tr>
              </thead>
              <tbody>
                {monthlyAverages(data).map((m) => (
                  <tr key={m.month}>
                    <td>{m.month}</td>
                    <td>{m.avg}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <p className="muted">
          Stage 3 compares the shaded windows on each side of the line. The earlier promo shows the same dip in April. That's the
          "same pattern as last quarter".
        </p>
      </div>

      <h3>All 50 tables in the database</h3>
      <p className="soft">
        Only 3 of them answer the question. 2 are decoys with sales-like names and misleading numbers. The rest are ordinary
        business tables.
      </p>
      <div className="table-legend">
        <span><i className="key source" /> the 3 right sources</span>
        <span><i className="key decoy" /> decoys</span>
        <span><i className="key other" /> everything else</span>
      </div>
      <div className="all-tables">
        {tables.map((t) => (
          <span key={t.name} className={`tbl role-${t.role}`}>
            {t.name}
            <em>{t.rows.toLocaleString()}</em>
          </span>
        ))}
      </div>
    </>
  );
}
