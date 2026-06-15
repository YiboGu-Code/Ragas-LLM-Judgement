import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import {
  clearRecentDatasets,
  clearRecentRuns,
  getRecentDatasets,
  getRecentRuns,
} from "../storage/recent";
import { useEffect, useState } from "react";

function NavItem(props: { to: string; label: string }) {
  return (
    <NavLink
      to={props.to}
      className={({ isActive }) =>
        isActive ? "nav-item nav-item-active" : "nav-item"
      }
    >
      {props.label}
    </NavLink>
  );
}

export default function Layout() {
  const navigate = useNavigate();
  const location = useLocation();
  const [openDatasetId, setOpenDatasetId] = useState("");
  const [openRunId, setOpenRunId] = useState("");
  const [recentDatasets, setRecentDatasets] = useState<string[]>(
    getRecentDatasets(),
  );
  const [recentRuns, setRecentRuns] = useState<string[]>(getRecentRuns());

  useEffect(() => {
    setRecentDatasets(getRecentDatasets());
    setRecentRuns(getRecentRuns());
  }, [location.pathname]);

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-title">LLM Eval</div>

        <div className="nav-section">
          <div className="nav-section-title">导航</div>
          <NavItem to="/datasets/upload" label="Datasets" />
          <NavItem to="/runs/create" label="Runs" />
          <NavItem to="/health" label="Health" />
          <NavItem to="/help" label="Help" />
        </div>

        <div className="nav-section">
          <div className="row">
            <div className="nav-section-title" style={{ margin: 0 }}>
              最近 Datasets
            </div>
            <button
              className="btn"
              type="button"
              style={{ marginLeft: "auto" }}
              onClick={() => {
                if (!window.confirm("确认清空最近 Datasets？")) return;
                clearRecentDatasets();
                setRecentDatasets([]);
              }}
              disabled={recentDatasets.length === 0}
            >
              清空
            </button>
          </div>
          <div className="recent-list">
            {recentDatasets.length === 0 ? (
              <div className="muted">暂无</div>
            ) : (
              recentDatasets.map((id) => (
                <button
                  key={id}
                  className="recent-btn"
                  type="button"
                  onClick={() =>
                    navigate(`/datasets/${encodeURIComponent(id)}`)
                  }
                >
                  {id}
                </button>
              ))
            )}
          </div>
          <div className="open-row">
            <input
              className="input"
              value={openDatasetId}
              onChange={(e) => setOpenDatasetId(e.target.value)}
              placeholder="dataset_id..."
            />
            <button
              className="btn"
              type="button"
              onClick={() => {
                const id = openDatasetId.trim();
                if (!id) return;
                navigate(`/datasets/${encodeURIComponent(id)}`);
              }}
            >
              打开
            </button>
          </div>
        </div>

        <div className="nav-section">
          <div className="row">
            <div className="nav-section-title" style={{ margin: 0 }}>
              最近 Runs
            </div>
            <button
              className="btn"
              type="button"
              style={{ marginLeft: "auto" }}
              onClick={() => {
                if (!window.confirm("确认清空最近 Runs？")) return;
                clearRecentRuns();
                setRecentRuns([]);
              }}
              disabled={recentRuns.length === 0}
            >
              清空
            </button>
          </div>
          <div className="recent-list">
            {recentRuns.length === 0 ? (
              <div className="muted">暂无</div>
            ) : (
              recentRuns.map((id) => (
                <button
                  key={id}
                  className="recent-btn"
                  type="button"
                  onClick={() => navigate(`/runs/${encodeURIComponent(id)}`)}
                >
                  {id}
                </button>
              ))
            )}
          </div>
          <div className="open-row">
            <input
              className="input"
              value={openRunId}
              onChange={(e) => setOpenRunId(e.target.value)}
              placeholder="run_id..."
            />
            <button
              className="btn"
              type="button"
              onClick={() => {
                const id = openRunId.trim();
                if (!id) return;
                navigate(`/runs/${encodeURIComponent(id)}`);
              }}
            >
              打开
            </button>
          </div>
        </div>
      </aside>

      <main className="main">
        <Outlet />
      </main>
    </div>
  );
}
