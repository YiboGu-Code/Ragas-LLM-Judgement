export class ApiError extends Error {
  status: number;
  detail: unknown;

  constructor(message: string, status: number, detail: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

type ApiFetchOptions = Omit<RequestInit, "body"> & {
  body?: unknown;
  isFormData?: boolean;
};

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function toErrorMessage(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map(toErrorMessage).join("\n");
  if (isObject(detail) && typeof detail.message === "string")
    return detail.message;
  return "Request failed";
}

export async function apiFetch<T>(
  path: string,
  options: ApiFetchOptions = {},
): Promise<T> {
  const url = path.startsWith("/api")
    ? path
    : `/api${path.startsWith("/") ? "" : "/"}${path}`;

  const headers = new Headers(options.headers);
  let body: BodyInit | undefined;

  if (options.isFormData) {
    body = options.body as BodyInit | undefined;
  } else if (options.body !== undefined) {
    headers.set("Content-Type", "application/json");
    body = JSON.stringify(options.body);
  }

  const res = await fetch(url, {
    ...options,
    headers,
    body,
  });

  if (res.ok) {
    const contentType = res.headers.get("content-type") ?? "";
    if (contentType.includes("application/json")) {
      return (await res.json()) as T;
    }
    return (await res.text()) as T;
  }

  const contentType = res.headers.get("content-type") ?? "";
  let detail: unknown = undefined;

  if (contentType.includes("application/json")) {
    try {
      const parsed = (await res.json()) as unknown;
      detail = isObject(parsed) && "detail" in parsed ? parsed.detail : parsed;
    } catch (e) {
      void e;
    }
  } else {
    try {
      detail = await res.text();
    } catch (e) {
      void e;
    }
  }

  throw new ApiError(toErrorMessage(detail), res.status, detail);
}

export async function apiFetchBlob(
  path: string,
  options: Omit<RequestInit, "body"> = {},
): Promise<Blob> {
  const url = path.startsWith("/api")
    ? path
    : `/api${path.startsWith("/") ? "" : "/"}${path}`;

  const res = await fetch(url, options);

  if (res.ok) {
    return await res.blob();
  }

  const contentType = res.headers.get("content-type") ?? "";
  let detail: unknown = undefined;

  if (contentType.includes("application/json")) {
    try {
      const parsed = (await res.json()) as unknown;
      detail = isObject(parsed) && "detail" in parsed ? parsed.detail : parsed;
    } catch (e) {
      void e;
    }
  } else {
    try {
      detail = await res.text();
    } catch (e) {
      void e;
    }
  }

  throw new ApiError(toErrorMessage(detail), res.status, detail);
}
