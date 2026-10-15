import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { newestRevision, repositoryFileContents } from "@/api"

// Node's Request rejects the relative URLs a browser resolves against the page, so resolve them here
vi.hoisted(() => {
    const NodeRequest = globalThis.Request
    globalThis.Request = class extends NodeRequest {
        constructor(input: RequestInfo | URL, init?: RequestInit) {
            super(typeof input === "string" ? new URL(input, "http://localhost") : input, init)
        }
    }
})

const fetchMock = vi.fn()

function jsonResponse(body: unknown, status = 200) {
    return new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } })
}

function requestedPath(): string {
    const request = fetchMock.mock.calls[0][0] as Request
    return new URL(request.url).pathname
}

describe("repository file API helpers", () => {
    beforeEach(() => {
        fetchMock.mockReset()
        vi.stubGlobal("fetch", fetchMock)
    })

    afterEach(() => {
        vi.unstubAllGlobals()
    })

    it("keeps the slashes of a file path real but escapes each segment", async () => {
        fetchMock.mockResolvedValue(jsonResponse({}))

        await repositoryFileContents("abc", "r1", "test data/a%b#c?.txt")

        expect(requestedPath()).toBe("/api/repositories/abc/revisions/r1/files/test%20data/a%25b%23c%3F.txt")
    })

    it("throws when the file is not found", async () => {
        fetchMock.mockResolvedValue(jsonResponse({ err_msg: "No such file" }, 404))

        await expect(repositoryFileContents("abc", "r1", "missing.txt")).rejects.toThrow("404")
    })
})

describe("newestRevision", () => {
    it("takes the last metadata entry, since keys run oldest to newest", () => {
        const metadata = {
            "0:aaaaaaaaaaaa": { changeset_revision: "aaaaaaaaaaaa" },
            "1:bbbbbbbbbbbb": { changeset_revision: "bbbbbbbbbbbb" },
        }
        expect(newestRevision(metadata)).toBe("bbbbbbbbbbbb")
    })

    it("is null without metadata", () => {
        expect(newestRevision({})).toBeNull()
        expect(newestRevision(null)).toBeNull()
        expect(newestRevision(undefined)).toBeNull()
    })
})
