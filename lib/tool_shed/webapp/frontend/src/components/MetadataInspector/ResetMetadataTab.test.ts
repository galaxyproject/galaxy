import { describe, it, expect, beforeEach, vi } from "vitest"
import { mount, flushPromises } from "@vue/test-utils"
import ResetMetadataTab from "./ResetMetadataTab.vue"
import { resetMetadataPreview, resetMetadataApplied, type ResetMetadataOnRepositoryResponse } from "./__fixtures__"

// Mock the API
const mockPost = vi.fn()
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

const fixturePreviewResponse = resetMetadataPreview
const fixtureApplyResponse = resetMetadataApplied

describe("ResetMetadataTab", () => {
    beforeEach(() => {
        vi.clearAllMocks()
    })

    describe("initial state", () => {
        it("displays info banner with Preview Changes button", () => {
            const wrapper = mount(ResetMetadataTab, {
                props: { repositoryId: "repo123" },
            })

            expect(wrapper.text()).toContain("Reset metadata")
            expect(wrapper.text()).toContain("regenerates all revision metadata")
            expect(wrapper.find("button").text()).toContain("Preview Changes")
        })

        it("lists use cases for reset", () => {
            const wrapper = mount(ResetMetadataTab, {
                props: { repositoryId: "repo123" },
            })

            expect(wrapper.text()).toContain("Fix corrupted tool_config paths")
            expect(wrapper.text()).toContain("Refresh metadata after tool shed code updates")
            expect(wrapper.text()).toContain("Repair missing or incomplete metadata")
        })
    })

    describe("preview", () => {
        it("calls API with dry_run=true when Preview Changes clicked", async () => {
            mockPost.mockResolvedValue({ data: fixturePreviewResponse })

            const wrapper = mount(ResetMetadataTab, {
                props: { repositoryId: "repo123" },
            })

            await wrapper.find("button").trigger("click")
            await flushPromises()

            expect(mockPost).toHaveBeenCalledWith(
                "/api/repositories/{encoded_repository_id}/reset_metadata",
                expect.objectContaining({
                    params: {
                        path: { encoded_repository_id: "repo123" },
                        query: { dry_run: true, verbose: true },
                    },
                })
            )
        })

        it("shows Preview Results with dry run indicator after preview", async () => {
            mockPost.mockResolvedValue({ data: fixturePreviewResponse })

            const wrapper = mount(ResetMetadataTab, {
                props: { repositoryId: "repo123" },
            })

            await wrapper.find("button").trigger("click")
            await flushPromises()

            expect(wrapper.text()).toContain("Preview Results")
            expect(wrapper.text()).toContain("(dry run)")
        })

        it("shows Apply Now button after preview", async () => {
            mockPost.mockResolvedValue({ data: fixturePreviewResponse })

            const wrapper = mount(ResetMetadataTab, {
                props: { repositoryId: "repo123" },
            })

            await wrapper.find("button").trigger("click")
            await flushPromises()

            const applyBtn = wrapper.findAll("button").find((b) => b.text().includes("Apply Now"))
            expect(applyBtn).toBeTruthy()
        })

        it("shows status chip with 'ok' for successful preview", async () => {
            mockPost.mockResolvedValue({ data: fixturePreviewResponse })

            const wrapper = mount(ResetMetadataTab, {
                props: { repositoryId: "repo123" },
            })

            await wrapper.find("button").trigger("click")
            await flushPromises()

            expect(wrapper.text()).toContain("ok")
        })
    })

    describe("apply reset", () => {
        it("calls API with dry_run=false when Apply Now clicked", async () => {
            mockPost.mockResolvedValueOnce({ data: fixturePreviewResponse })
            mockPost.mockResolvedValueOnce({ data: fixtureApplyResponse })

            const wrapper = mount(ResetMetadataTab, {
                props: { repositoryId: "repo123" },
            })

            // Preview first
            await wrapper.find("button").trigger("click")
            await flushPromises()

            // Apply
            const applyBtn = wrapper.findAll("button").find((b) => b.text().includes("Apply Now"))
            await applyBtn!.trigger("click")
            await flushPromises()

            expect(mockPost).toHaveBeenLastCalledWith(
                "/api/repositories/{encoded_repository_id}/reset_metadata",
                expect.objectContaining({
                    params: {
                        path: { encoded_repository_id: "repo123" },
                        query: { dry_run: false, verbose: true },
                    },
                })
            )
        })

        it("shows Reset Complete without dry run indicator after apply", async () => {
            mockPost.mockResolvedValueOnce({ data: fixturePreviewResponse })
            mockPost.mockResolvedValueOnce({ data: fixtureApplyResponse })

            const wrapper = mount(ResetMetadataTab, {
                props: { repositoryId: "repo123" },
            })

            await wrapper.find("button").trigger("click")
            await flushPromises()

            const applyBtn = wrapper.findAll("button").find((b) => b.text().includes("Apply Now"))
            await applyBtn!.trigger("click")
            await flushPromises()

            expect(wrapper.text()).toContain("Reset Complete")
            expect(wrapper.text()).not.toContain("(dry run)")
        })

        it("hides Apply Now button after successful apply", async () => {
            mockPost.mockResolvedValueOnce({ data: fixturePreviewResponse })
            mockPost.mockResolvedValueOnce({ data: fixtureApplyResponse })

            const wrapper = mount(ResetMetadataTab, {
                props: { repositoryId: "repo123" },
            })

            await wrapper.find("button").trigger("click")
            await flushPromises()

            const applyBtn = wrapper.findAll("button").find((b) => b.text().includes("Apply Now"))
            await applyBtn!.trigger("click")
            await flushPromises()

            const postApplyApplyBtn = wrapper.findAll("button").find((b) => b.text().includes("Apply Now"))
            expect(postApplyApplyBtn).toBeFalsy()
        })
    })

    describe("new preview / clear", () => {
        it("returns to initial state when New Preview clicked", async () => {
            mockPost.mockResolvedValue({ data: fixturePreviewResponse })

            const wrapper = mount(ResetMetadataTab, {
                props: { repositoryId: "repo123" },
            })

            await wrapper.find("button").trigger("click")
            await flushPromises()

            const newPreviewBtn = wrapper.findAll("button").find((b) => b.text().includes("New Preview"))
            await newPreviewBtn!.trigger("click")
            await flushPromises()

            expect(wrapper.text()).toContain("Reset metadata")
            expect(wrapper.text()).toContain("Preview Changes")
        })

        it("emits resetComplete when clearing after non-dry-run reset", async () => {
            mockPost.mockResolvedValueOnce({ data: fixturePreviewResponse })
            mockPost.mockResolvedValueOnce({ data: fixtureApplyResponse })

            const wrapper = mount(ResetMetadataTab, {
                props: { repositoryId: "repo123" },
            })

            // Preview -> Apply -> Clear
            await wrapper.find("button").trigger("click")
            await flushPromises()

            const applyBtn = wrapper.findAll("button").find((b) => b.text().includes("Apply Now"))
            await applyBtn!.trigger("click")
            await flushPromises()

            const newPreviewBtn = wrapper.findAll("button").find((b) => b.text().includes("New Preview"))
            await newPreviewBtn!.trigger("click")
            await flushPromises()

            expect(wrapper.emitted("resetComplete")).toBeTruthy()
        })

        it("does not emit resetComplete when clearing after dry run only", async () => {
            mockPost.mockResolvedValue({ data: fixturePreviewResponse })

            const wrapper = mount(ResetMetadataTab, {
                props: { repositoryId: "repo123" },
            })

            await wrapper.find("button").trigger("click")
            await flushPromises()

            const newPreviewBtn = wrapper.findAll("button").find((b) => b.text().includes("New Preview"))
            await newPreviewBtn!.trigger("click")
            await flushPromises()

            expect(wrapper.emitted("resetComplete")).toBeFalsy()
        })
    })

    describe("view modes", () => {
        it("shows Summary Table by default", async () => {
            mockPost.mockResolvedValue({ data: fixturePreviewResponse })

            const wrapper = mount(ResetMetadataTab, {
                props: { repositoryId: "repo123" },
            })

            await wrapper.find("button").trigger("click")
            await flushPromises()

            expect(wrapper.find(".mock-summary-table").exists()).toBe(true)
        })

        it("has toggle between Summary Table and JSON Diff", async () => {
            mockPost.mockResolvedValue({ data: fixturePreviewResponse })

            const wrapper = mount(ResetMetadataTab, {
                props: { repositoryId: "repo123" },
            })

            await wrapper.find("button").trigger("click")
            await flushPromises()

            expect(wrapper.text()).toContain("Summary Table")
            expect(wrapper.text()).toContain("JSON Diff")
        })
    })

    describe("error handling", () => {
        it("calls notifyOnCatch when API fails", async () => {
            const { notifyOnCatch } = await import("@/util")
            mockPost.mockRejectedValue(new Error("API Error"))

            const wrapper = mount(ResetMetadataTab, {
                props: { repositoryId: "repo123" },
            })

            await wrapper.find("button").trigger("click")
            await flushPromises()

            expect(notifyOnCatch).toHaveBeenCalled()
        })
    })

    describe("edge cases", () => {
        it("shows message when response has no changeset details", async () => {
            const noDetailsResponse: ResetMetadataOnRepositoryResponse = {
                ...fixturePreviewResponse,
                changeset_details: null,
            }
            mockPost.mockResolvedValue({ data: noDetailsResponse })

            const wrapper = mount(ResetMetadataTab, {
                props: { repositoryId: "repo123" },
            })

            await wrapper.find("button").trigger("click")
            await flushPromises()

            expect(wrapper.text()).toContain("No changeset details available")
        })

        it("displays warning status when API returns warning", async () => {
            const warningResponse: ResetMetadataOnRepositoryResponse = {
                ...fixturePreviewResponse,
                status: "warning",
            }
            mockPost.mockResolvedValue({ data: warningResponse })

            const wrapper = mount(ResetMetadataTab, {
                props: { repositoryId: "repo123" },
            })

            await wrapper.find("button").trigger("click")
            await flushPromises()

            expect(wrapper.text()).toContain("warning")
        })
    })
})
