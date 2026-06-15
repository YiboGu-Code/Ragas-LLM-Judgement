import { afterEach, describe, expect, it, vi } from "vitest";
import { bulkDeleteDatasets, listDatasets } from "./datasets";

describe("listDatasets", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("requests shared dataset list from /datasets", async () => {
    const fetchMock = vi.fn(
      async () =>
        new Response(
          JSON.stringify({
            items: [
              {
                dataset_id: "ds-1",
                name: "shared",
                eval_type: "prompt",
                schema_version: "v1",
                records_count: 1,
                created_at: "2026-06-10T00:00:00Z",
              },
            ],
          }),
          { status: 200, headers: { "content-type": "application/json" } },
        ),
    );
    vi.stubGlobal("fetch", fetchMock);

    const res = await listDatasets();

    expect(fetchMock).toHaveBeenCalledWith("/api/datasets", expect.any(Object));
    expect(res.items[0].dataset_id).toBe("ds-1");
  });
});

describe("bulkDeleteDatasets", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("posts dataset_ids to /datasets/bulk-delete", async () => {
    const fetchMock = vi.fn(
      async () =>
        new Response(
          JSON.stringify({
            results: [{ id: "ds-1", status: "deleted", detail: null }],
          }),
          { status: 200, headers: { "content-type": "application/json" } },
        ),
    );
    vi.stubGlobal("fetch", fetchMock);

    const res = await bulkDeleteDatasets(["ds-1"]);

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/datasets/bulk-delete",
      expect.objectContaining({ method: "POST" }),
    );
    expect(res.results[0].id).toBe("ds-1");
  });
});
