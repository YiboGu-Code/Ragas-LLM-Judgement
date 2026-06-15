import { beforeEach, describe, expect, it } from "vitest";
import {
  addRecentDataset,
  addRecentRun,
  clearRecentDatasets,
  clearRecentRuns,
  getRecentDatasets,
  getRecentRuns,
} from "./recent";

describe("recent storage", () => {
  beforeEach(() => {
    const store = new Map<string, string>();
    // Minimal localStorage mock for vitest node environment
    (globalThis as any).localStorage = {
      getItem: (key: string) => store.get(key) ?? null,
      setItem: (key: string, value: string) => {
        store.set(key, String(value));
      },
      removeItem: (key: string) => {
        store.delete(key);
      },
      clear: () => {
        store.clear();
      },
    };
    localStorage.clear();
  });

  it("adds new dataset ids to the top, but does not reorder on duplicate add", () => {
    addRecentDataset("ds-1");
    addRecentDataset("ds-2");
    expect(getRecentDatasets()).toEqual(["ds-2", "ds-1"]);

    addRecentDataset("ds-1");
    expect(getRecentDatasets()).toEqual(["ds-2", "ds-1"]);
  });

  it("adds new run ids to the top, but does not reorder on duplicate add", () => {
    addRecentRun("run-1");
    addRecentRun("run-2");
    expect(getRecentRuns()).toEqual(["run-2", "run-1"]);

    addRecentRun("run-1");
    expect(getRecentRuns()).toEqual(["run-2", "run-1"]);
  });

  it("clears recent datasets and runs", () => {
    addRecentDataset("ds-1");
    addRecentRun("run-1");
    expect(getRecentDatasets()).toEqual(["ds-1"]);
    expect(getRecentRuns()).toEqual(["run-1"]);

    clearRecentDatasets();
    clearRecentRuns();
    expect(getRecentDatasets()).toEqual([]);
    expect(getRecentRuns()).toEqual([]);
  });
});
