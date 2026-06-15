import { afterEach, describe, expect, it, vi } from "vitest";
import { bulkDeleteRuns, listRuns } from "./runs";

describe("listRuns", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("requests shared run list from /runs", async () => {
    const fetchMock = vi.fn(
      async () =>
        new Response(
          JSON.stringify({
            items: [
              {
                run_id: "run-1",
                dataset_id: "ds-1",
                eval_type: "prompt",
                status: "succeeded",
                progress: { total: 1, completed: 1, failed: 0 },
                created_at: "2026-06-10T00:00:00Z",
                started_at: "2026-06-10T00:00:01Z",
                finished_at: "2026-06-10T00:00:02Z",
              },
            ],
          }),
          { status: 200, headers: { "content-type": "application/json" } },
        ),
    );
    vi.stubGlobal("fetch", fetchMock);

    const res = await listRuns();

    expect(fetchMock).toHaveBeenCalledWith("/api/runs", expect.any(Object));
    expect(res.items[0].run_id).toBe("run-1");
  });
});

describe("bulkDeleteRuns", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("posts run_ids to /runs/bulk-delete", async () => {
    const fetchMock = vi.fn(
      async () =>
        new Response(
          JSON.stringify({
            results: [{ id: "run-1", status: "deleted", detail: null }],
          }),
          { status: 200, headers: { "content-type": "application/json" } },
        ),
    );
    vi.stubGlobal("fetch", fetchMock);

    const res = await bulkDeleteRuns(["run-1"]);

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/runs/bulk-delete",
      expect.objectContaining({ method: "POST" }),
    );
    expect(res.results[0].id).toBe("run-1");
  });
});
