import { beforeEach, describe, expect, it, vi } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";
import { retryBackoffMs } from "@/utils/simple-error";

import { deleteJob, stopJobs } from "./jobs";

vi.mock("@/utils/simple-error", async (importOriginal) => ({
    ...(await importOriginal<object>()),
    retryBackoffMs: vi.fn(() => 0),
}));

const { server, http } = useServerMock();

beforeEach(() => {
    // The GalaxyApi rate limiter logs its 429 retries.
    vi.spyOn(console, "warn").mockImplementation(() => {});
    vi.spyOn(console, "error").mockImplementation(() => {});
});

function tooManyRequests(headers: Record<string, string> = {}) {
    return HttpResponse.json({ err_msg: "Too Many Requests" }, { status: 429, headers });
}

describe("deleteJob", () => {
    it("sends the stop message in the request body", async () => {
        let body: unknown;
        server.use(
            http.delete("/api/jobs/{job_id}", async ({ request, response }) => {
                body = await request.json();
                return response(200).json(true);
            }),
        );

        await deleteJob("job1", "maintenance");

        expect(body).toEqual({ message: "maintenance" });
    });

    it("sends no body without a stop message", async () => {
        let body: string | undefined;
        server.use(
            http.delete("/api/jobs/{job_id}", async ({ request, response }) => {
                body = await request.text();
                return response(200).json(true);
            }),
        );

        await deleteJob("job1");

        expect(body).toBe("");
    });
});

describe("stopJobs", () => {
    it("retries rate-limited jobs until they stop", async () => {
        const attempts: Record<string, number> = {};
        const bodies: unknown[] = [];
        server.use(
            http.delete("/api/jobs/{job_id}", async ({ params, request, response }) => {
                attempts[params.job_id] = (attempts[params.job_id] ?? 0) + 1;
                if (params.job_id === "job2") {
                    bodies.push(await request.json());
                }
                if (params.job_id === "job2" && (attempts[params.job_id] ?? 0) < 3) {
                    return response.untyped(tooManyRequests());
                }
                return response(200).json(true);
            }),
        );

        const result = await stopJobs(["job1", "job2"], "maintenance");

        expect(result.stopped.sort()).toEqual(["job1", "job2"]);
        expect(result.failed).toEqual([]);
        expect(attempts).toEqual({ job1: 1, job2: 3 });
        // Retries resend the stop message.
        expect(bodies).toEqual(Array(3).fill({ message: "maintenance" }));
    });

    it("reports jobs that keep failing without rejecting", async () => {
        const attempts: Record<string, number> = {};
        server.use(
            http.delete("/api/jobs/{job_id}", ({ params, response }) => {
                attempts[params.job_id] = (attempts[params.job_id] ?? 0) + 1;
                if (params.job_id === "limited") {
                    return response.untyped(tooManyRequests());
                }
                if (params.job_id === "forbidden") {
                    return response.untyped(HttpResponse.json({ err_msg: "Not yours" }, { status: 403 }));
                }
                if (params.job_id === "long-wait") {
                    return response.untyped(tooManyRequests({ "Retry-After": "600" }));
                }
                return response(200).json(true);
            }),
        );
        const progress: number[] = [];

        const result = await stopJobs(["ok", "limited", "forbidden", "long-wait"], undefined, (done) =>
            progress.push(done),
        );

        expect(result.stopped).toEqual(["ok"]);
        expect(result.failed.map(({ jobId }) => jobId).sort()).toEqual(["forbidden", "limited", "long-wait"]);
        expect(result.failed.find(({ jobId }) => jobId === "forbidden")?.error.message).toBe("Not yours");
        // Initial attempt plus the rate limiter's retries; client errors and long Retry-After are not retried.
        expect(attempts).toEqual({ ok: 1, limited: 4, forbidden: 1, "long-wait": 1 });
        expect(progress).toEqual([1, 2, 3, 4]);
    });

    it("pauses every worker while one waits out a rate limit", async () => {
        vi.mocked(retryBackoffMs).mockReturnValueOnce(100);
        let limitedAt: number | undefined;
        const startedAfterLimit: number[] = [];
        // Sent alongside "limited" before its 429 came back.
        const firstBatch = ["job0", "job1", "job2"];
        server.use(
            http.delete("/api/jobs/{job_id}", async ({ params, response }) => {
                if (limitedAt !== undefined && !firstBatch.includes(params.job_id as string)) {
                    startedAfterLimit.push(Date.now() - limitedAt);
                }
                if (params.job_id === "limited" && limitedAt === undefined) {
                    limitedAt = Date.now();
                    return response.untyped(tooManyRequests());
                }
                await new Promise((resolve) => setTimeout(resolve, 5));
                return response(200).json(true);
            }),
        );
        const jobIds = ["limited", ...Array.from({ length: 8 }, (_, i) => `job${i}`)];

        const result = await stopJobs(jobIds);

        expect(result.stopped).toHaveLength(9);
        expect(startedAfterLimit.length).toBeGreaterThan(0);
        // Small slack for timer granularity.
        expect(Math.min(...startedAfterLimit)).toBeGreaterThanOrEqual(90);
    });

    it("stops sending once a rate-limited job gives up", async () => {
        const attempts: Record<string, number> = {};
        server.use(
            http.delete("/api/jobs/{job_id}", async ({ params, response }) => {
                attempts[params.job_id] = (attempts[params.job_id] ?? 0) + 1;
                if (params.job_id === "long-wait") {
                    return response.untyped(tooManyRequests({ "Retry-After": "600" }));
                }
                await new Promise((resolve) => setTimeout(resolve, 5));
                return response(200).json(true);
            }),
        );
        const jobIds = ["long-wait", "a", "b", "c", "d", "e", "f"];

        const result = await stopJobs(jobIds);

        // Jobs already in flight finish; queued ones are not sent.
        expect(attempts).toEqual({ "long-wait": 1, a: 1, b: 1, c: 1 });
        expect(result.stopped.sort()).toEqual(["a", "b", "c"]);
        expect(result.failed.map(({ jobId }) => jobId).sort()).toEqual(["d", "e", "f", "long-wait"]);
        expect(new Set(result.failed.map(({ error }) => error.message))).toEqual(new Set(["Too Many Requests"]));
    });

    it("keeps stopping other jobs after a server error", async () => {
        const attempts: Record<string, number> = {};
        server.use(
            http.delete("/api/jobs/{job_id}", ({ params, response }) => {
                attempts[params.job_id] = (attempts[params.job_id] ?? 0) + 1;
                if (params.job_id === "broken") {
                    return response.untyped(HttpResponse.json({ err_msg: "Server Error" }, { status: 500 }));
                }
                return response(200).json(true);
            }),
        );
        const jobIds = ["broken", "a", "b", "c", "d", "e", "f"];

        const result = await stopJobs(jobIds);

        expect(attempts.broken).toBe(1);
        expect(result.stopped.sort()).toEqual(["a", "b", "c", "d", "e", "f"]);
        expect(result.failed.map(({ jobId }) => jobId)).toEqual(["broken"]);
    });

    it("limits how many stop requests are in flight", async () => {
        let inFlight = 0;
        let maxInFlight = 0;
        server.use(
            http.delete("/api/jobs/{job_id}", async ({ response }) => {
                inFlight++;
                maxInFlight = Math.max(maxInFlight, inFlight);
                await new Promise((resolve) => setTimeout(resolve, 5));
                inFlight--;
                return response(200).json(true);
            }),
        );
        const jobIds = Array.from({ length: 20 }, (_, i) => `job${i}`);

        const result = await stopJobs(jobIds);

        expect(result.stopped).toHaveLength(20);
        expect(maxInFlight).toBeLessThanOrEqual(4);
        expect(maxInFlight).toBeGreaterThan(1);
    });
});
