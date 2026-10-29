import { describe, expect, it, vi } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";

import { deleteJob, stopJobs } from "./jobs";

vi.mock("@/utils/simple-error", async (importOriginal) => ({
    ...(await importOriginal<object>()),
    retryBackoffMs: () => 0,
}));

const { server, http } = useServerMock();

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
        server.use(
            http.delete("/api/jobs/{job_id}", ({ params, response }) => {
                attempts[params.job_id] = (attempts[params.job_id] ?? 0) + 1;
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
        // Initial attempt plus MAX_RETRIES; client errors and long Retry-After are not retried.
        expect(attempts).toEqual({ ok: 1, limited: 4, forbidden: 1, "long-wait": 1 });
        expect(progress).toEqual([1, 2, 3, 4]);
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
