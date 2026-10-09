import { afterEach, describe, it, expect, beforeEach, vi } from "vitest"
import { enableAutoUnmount, mount, flushPromises } from "@vue/test-utils"
import ResetMetadataTab from "./ResetMetadataTab.vue"
import { resetMetadataPreview, resetMetadataApplied, type ResetMetadataOnRepositoryResponse } from "./__fixtures__"

// Mock the API
const { mockPost } = vi.hoisted(() => ({ mockPost: vi.fn() }))
vi.mock("@/schema", () => ({
    ToolShedApi: () => ({
        POST: mockPost,
    }),
}))

// Mock notifyOnCatch
vi.mock("@/util", () => ({
    notifyOnCatch: vi.fn(),
}))

// Mock child components
vi.mock("./ChangesetSummaryTable.vue", () => ({
    default: {
        name: "ChangesetSummaryTable",
        props: ["changesets"],
        template: '<div class="mock-summary-table">{{ changesets.length }} changesets</div>',
    },
}))
vi.mock("./JsonDiffViewer.vue", () => ({
    default: {
        name: "JsonDiffViewer",
        props: ["before", "after"],
        template: '<div class="mock-diff-viewer">Diff viewer</div>',
    },
}))

enableAutoUnmount(afterEach)

function mountTab() {
    return mount(ResetMetadataTab, { props: { repositoryId: "repo123" } })
}

function findButton(wrapper: ReturnType<typeof mountTab>, text: string) {
    return wrapper.findAll("button").find((button) => button.text().includes(text))
}

function getButton(wrapper: ReturnType<typeof mountTab>, text: string) {
    const button = findButton(wrapper, text)
    if (!button) throw new Error(`Expected a button containing "${text}"`)
    return button
}

async function clickButton(wrapper: ReturnType<typeof mountTab>, text: string) {
    await getButton(wrapper, text).trigger("click")
    await flushPromises()
}

describe("ResetMetadataTab", () => {
    beforeEach(() => {
        vi.resetAllMocks()
    })

    describe("initial state", () => {
        it("displays info banner with Preview Changes button", () => {
            const wrapper = mountTab()

            expect(wrapper.text()).toContain("Reset metadata")
            expect(wrapper.text()).toContain("regenerates all revision metadata")
            expect(getButton(wrapper, "Preview Changes").text()).toContain("Preview Changes")
        })

        it("lists use cases for reset", () => {
            const wrapper = mountTab()

            expect(wrapper.text()).toContain("Fix corrupted tool_config paths")
            expect(wrapper.text()).toContain("Refresh metadata after tool shed code updates")
            expect(wrapper.text()).toContain("Repair missing or incomplete metadata")
        })
    })

    describe("preview", () => {
        it("calls API with dry_run=true when Preview Changes clicked", async () => {
            mockPost.mockResolvedValue({ data: resetMetadataPreview })

            const wrapper = mountTab()

            await clickButton(wrapper, "Preview Changes")

            expect(mockPost).toHaveBeenCalledWith(
                "/api/repositories/{encoded_repository_id}/reset_metadata",
                expect.objectContaining({
                    params: {
                        path: { encoded_repository_id: "repo123" },
                        query: { dry_run: true, verbose: true },
                    },
                }),
            )
        })

        it("shows Preview Results with dry run indicator after preview", async () => {
            mockPost.mockResolvedValue({ data: resetMetadataPreview })

            const wrapper = mountTab()

            await clickButton(wrapper, "Preview Changes")

            expect(wrapper.text()).toContain("Preview Results")
            expect(wrapper.text()).toContain("(dry run)")
        })

        it("shows Apply Now button after preview", async () => {
            mockPost.mockResolvedValue({ data: resetMetadataPreview })

            const wrapper = mountTab()

            await clickButton(wrapper, "Preview Changes")

            const applyBtn = findButton(wrapper, "Apply Now")
            expect(applyBtn).toBeTruthy()
        })

        it("shows status chip with 'ok' for successful preview", async () => {
            mockPost.mockResolvedValue({ data: resetMetadataPreview })

            const wrapper = mountTab()

            await clickButton(wrapper, "Preview Changes")

            expect(wrapper.text()).toContain("ok")
            expect(wrapper.find(".reset-status-chip--ok").exists()).toBe(true)
        })

        it("keeps the accessible name on the Preview Changes button while loading", async () => {
            let resolvePost!: (value: { data: ResetMetadataOnRepositoryResponse }) => void
            mockPost.mockReturnValue(
                new Promise((resolve) => {
                    resolvePost = resolve
                }),
            )

            const wrapper = mountTab()

            const button = getButton(wrapper, "Preview Changes")
            await button.trigger("click")

            expect(button.attributes("aria-busy")).toBe("true")
            expect(button.text()).toContain("Preview Changes")

            resolvePost({ data: resetMetadataPreview })
            await flushPromises()
        })
    })

    describe("apply reset", () => {
        it("calls API with dry_run=false when Apply Now clicked", async () => {
            mockPost.mockResolvedValueOnce({ data: resetMetadataPreview })
            mockPost.mockResolvedValueOnce({ data: resetMetadataApplied })

            const wrapper = mountTab()

            await clickButton(wrapper, "Preview Changes")

            await clickButton(wrapper, "Apply Now")

            expect(mockPost).toHaveBeenLastCalledWith(
                "/api/repositories/{encoded_repository_id}/reset_metadata",
                expect.objectContaining({
                    params: {
                        path: { encoded_repository_id: "repo123" },
                        query: { dry_run: false, verbose: true },
                    },
                }),
            )
        })

        it("shows Reset Complete without dry run indicator after apply", async () => {
            mockPost.mockResolvedValueOnce({ data: resetMetadataPreview })
            mockPost.mockResolvedValueOnce({ data: resetMetadataApplied })

            const wrapper = mountTab()

            await clickButton(wrapper, "Preview Changes")

            await clickButton(wrapper, "Apply Now")

            expect(wrapper.text()).toContain("Reset Complete")
            expect(wrapper.text()).not.toContain("(dry run)")
        })

        it("hides Apply Now button after successful apply", async () => {
            mockPost.mockResolvedValueOnce({ data: resetMetadataPreview })
            mockPost.mockResolvedValueOnce({ data: resetMetadataApplied })

            const wrapper = mountTab()

            await clickButton(wrapper, "Preview Changes")

            await clickButton(wrapper, "Apply Now")

            const postApplyApplyBtn = findButton(wrapper, "Apply Now")
            expect(postApplyApplyBtn).toBeFalsy()
        })
    })

    describe("new preview / clear", () => {
        it("returns to initial state when New Preview clicked", async () => {
            mockPost.mockResolvedValue({ data: resetMetadataPreview })

            const wrapper = mountTab()

            await clickButton(wrapper, "Preview Changes")

            await clickButton(wrapper, "New Preview")

            expect(wrapper.text()).toContain("Reset metadata")
            expect(wrapper.text()).toContain("Preview Changes")
        })

        it("emits resetComplete when clearing after non-dry-run reset", async () => {
            mockPost.mockResolvedValueOnce({ data: resetMetadataPreview })
            mockPost.mockResolvedValueOnce({ data: resetMetadataApplied })

            const wrapper = mountTab()

            await clickButton(wrapper, "Preview Changes")

            await clickButton(wrapper, "Apply Now")

            await clickButton(wrapper, "New Preview")

            expect(wrapper.emitted("resetComplete")).toEqual([[]])
        })

        it("does not emit resetComplete when clearing after dry run only", async () => {
            mockPost.mockResolvedValue({ data: resetMetadataPreview })

            const wrapper = mountTab()

            await clickButton(wrapper, "Preview Changes")

            await clickButton(wrapper, "New Preview")

            expect(wrapper.emitted("resetComplete")).toBeFalsy()
        })
    })

    describe("view modes", () => {
        it("shows Summary Table by default", async () => {
            mockPost.mockResolvedValue({ data: resetMetadataPreview })

            const wrapper = mountTab()

            await clickButton(wrapper, "Preview Changes")

            expect(wrapper.find(".mock-summary-table").exists()).toBe(true)
        })

        it("has toggle between Summary Table and JSON Diff", async () => {
            mockPost.mockResolvedValue({ data: resetMetadataPreview })

            const wrapper = mountTab()

            await clickButton(wrapper, "Preview Changes")

            expect(wrapper.text()).toContain("Summary Table")
            expect(wrapper.text()).toContain("JSON Diff")
        })

        it("marks the active view mode button with aria-pressed", async () => {
            mockPost.mockResolvedValue({ data: resetMetadataPreview })

            const wrapper = mountTab()

            await clickButton(wrapper, "Preview Changes")

            const tableButton = getButton(wrapper, "Summary Table")
            const diffButton = getButton(wrapper, "JSON Diff")

            expect(tableButton.attributes("aria-pressed")).toBe("true")
            expect(diffButton.attributes("aria-pressed")).toBe("false")
        })

        it("switches to the JSON diff view when its toggle button is clicked", async () => {
            mockPost.mockResolvedValue({ data: resetMetadataPreview })

            const wrapper = mountTab()

            await clickButton(wrapper, "Preview Changes")

            const diffButton = getButton(wrapper, "JSON Diff")
            await diffButton.trigger("click")

            expect(wrapper.find(".mock-diff-viewer").exists()).toBe(true)
            expect(wrapper.find(".mock-summary-table").exists()).toBe(false)
            expect(diffButton.attributes("aria-pressed")).toBe("true")
        })
    })

    describe("error handling", () => {
        it("calls notifyOnCatch when API fails", async () => {
            const { notifyOnCatch } = await import("@/util")
            mockPost.mockRejectedValue(new Error("API Error"))

            const wrapper = mountTab()

            await clickButton(wrapper, "Preview Changes")

            expect(notifyOnCatch).toHaveBeenCalled()
        })
    })

    describe("edge cases", () => {
        it("shows message when response has no changeset details", async () => {
            const noDetailsResponse: ResetMetadataOnRepositoryResponse = {
                ...resetMetadataPreview,
                changeset_details: null,
            }
            mockPost.mockResolvedValue({ data: noDetailsResponse })

            const wrapper = mountTab()

            await clickButton(wrapper, "Preview Changes")

            expect(wrapper.text()).toContain("No changeset details available")
        })

        it("displays warning status when API returns warning", async () => {
            const warningResponse: ResetMetadataOnRepositoryResponse = {
                ...resetMetadataPreview,
                status: "warning",
            }
            mockPost.mockResolvedValue({ data: warningResponse })

            const wrapper = mountTab()

            await clickButton(wrapper, "Preview Changes")

            expect(wrapper.text()).toContain("warning")
            expect(wrapper.find(".reset-status-chip--warning").exists()).toBe(true)
        })
    })
})
