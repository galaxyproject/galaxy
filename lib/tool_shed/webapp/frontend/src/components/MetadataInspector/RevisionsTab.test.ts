import { afterEach, describe, it, expect } from "vitest"
import { enableAutoUnmount, mount } from "@vue/test-utils"
import { nextTick } from "vue"
import RevisionsTab from "./RevisionsTab.vue"
import {
    repositoryMetadataColumnMaker,
    repositoryMetadataBismark,
    makeRevision,
    type RepositoryMetadata,
} from "./__fixtures__"

import { MetadataJsonViewerStub } from "./test-utils"

enableAutoUnmount(afterEach)

const fixtureMetadata = repositoryMetadataColumnMaker
const bismarkMetadata = repositoryMetadataBismark

function mountTab(props: { metadata: RepositoryMetadata | null; expandRevision?: string | null }) {
    return mount(RevisionsTab, {
        props,
        global: { stubs: { MetadataJsonViewer: MetadataJsonViewerStub } },
    })
}

describe("RevisionsTab", () => {
    describe("rendering", () => {
        it("displays 'No revisions found' when metadata is null", () => {
            const wrapper = mountTab({ metadata: null })

            expect(wrapper.text()).toContain("No revisions found")
        })

        it("displays 'No revisions found' when metadata is empty", () => {
            const wrapper = mountTab({ metadata: {} })

            expect(wrapper.text()).toContain("No revisions found")
        })

        it("displays list of revisions", () => {
            const wrapper = mountTab({ metadata: fixtureMetadata })

            expect(wrapper.find(".revision-list").exists()).toBe(true)
        })

        it("shows revision identifiers in format [num:hash]", () => {
            const wrapper = mountTab({ metadata: fixtureMetadata })

            const summaries = wrapper.findAll(".revision-summary")
            expect(summaries.map((summary) => summary.get("div").text())).toEqual([
                "[2:062143f]",
                "[1:191823a]",
                "[0:d6e7311]",
            ])
        })
    })

    describe("sorting", () => {
        it("sorts revisions with newest first", () => {
            const wrapper = mountTab({ metadata: fixtureMetadata })

            expect(wrapper.findAll(".revision-toggle").map((toggle) => toggle.attributes("aria-label"))).toEqual([
                "Details for revision 2",
                "Details for revision 1",
                "Details for revision 0",
            ])
        })
    })

    describe("tool summary", () => {
        it("shows tool ID for revisions with tools", () => {
            const wrapper = mountTab({ metadata: fixtureMetadata })

            expect(wrapper.text()).toContain("Add_a_column1")
        })

        it("shows 'No tools' for revisions without tools", () => {
            const noToolsMetadata: RepositoryMetadata = {
                "0:notools": makeRevision({ tools: [] }),
            }

            const wrapper = mountTab({ metadata: noToolsMetadata })

            expect(wrapper.text()).toContain("No tools")
        })
    })

    describe("invalid tools", () => {
        it("shows badge for revisions with invalid tools", () => {
            const wrapper = mountTab({ metadata: bismarkMetadata })

            expect(wrapper.text()).toContain("1 invalid")
            expect(wrapper.findAll(".invalid-tools-badge").map((badge) => badge.text())).toEqual([
                "2 invalid",
                "1 invalid",
            ])
        })

        it("shows no badge for revisions without invalid tools", () => {
            const wrapper = mountTab({ metadata: fixtureMetadata })

            expect(wrapper.find(".invalid-tools-badge").exists()).toBe(false)
        })

        it("shows invalid tool paths when revision is expanded", async () => {
            const wrapper = mountTab({
                metadata: bismarkMetadata,
                expandRevision: "0:c35bbde3c5e0",
            })

            await nextTick()

            const invalidTools = wrapper.get(".invalid-tools-list")
            expect(invalidTools.text()).toContain("bismark_bowtie_wrapper.xml")
            expect(invalidTools.text()).toContain("Tool XML parsing error")
        })
    })

    describe("expandRevision prop", () => {
        it("auto-expands revision when expandRevision prop is set", async () => {
            const wrapper = mountTab({
                metadata: fixtureMetadata,
                expandRevision: "0:d6e73113c7a5",
            })

            await nextTick()

            expect(wrapper.find(".mock-json-viewer").exists()).toBe(true)
        })

        it("expands new revision when expandRevision prop changes", async () => {
            const wrapper = mountTab({
                metadata: fixtureMetadata,
                expandRevision: null,
            })

            const expandedToggles = () => wrapper.findAll(".revision-toggle[aria-expanded=true]")
            expect(expandedToggles().length).toBe(0)
            expect(wrapper.find(".mock-json-viewer").exists()).toBe(false)

            await wrapper.setProps({ expandRevision: "0:d6e73113c7a5" })

            expect(expandedToggles().length).toBe(1)
            expect(wrapper.findAll(".mock-json-viewer").length).toBe(1)
        })
    })

    describe("expansion items", () => {
        it("renders one expansion item per revision", () => {
            const wrapper = mountTab({ metadata: fixtureMetadata })

            const toggles = wrapper.findAll(".revision-toggle")
            expect(toggles.length).toBe(Object.keys(fixtureMetadata).length)
        })

        it("toggles a revision's details from its button", async () => {
            const wrapper = mountTab({ metadata: fixtureMetadata })

            const toggle = wrapper.find(".revision-toggle")
            expect(toggle.element.tagName).toBe("BUTTON")
            expect(toggle.attributes("aria-expanded")).toBe("false")
            expect(toggle.attributes("aria-label")).toMatch(/^Details for revision \d+$/)

            const details = wrapper.find(`#${toggle.attributes("aria-controls")}`)
            expect(details.exists()).toBe(true)
            expect(details.find(".mock-json-viewer").exists()).toBe(false)

            await toggle.trigger("click")

            expect(toggle.attributes("aria-expanded")).toBe("true")
            expect(details.find(".mock-json-viewer").exists()).toBe(true)

            await toggle.trigger("click")

            expect(toggle.attributes("aria-expanded")).toBe("false")
        })
    })

    describe("edge cases", () => {
        it("handles revision with many invalid tools", () => {
            const manyInvalidMetadata: RepositoryMetadata = {
                "0:invalidtools": makeRevision({
                    tools: [],
                    downloadable: false,
                    invalid_tools: [
                        { tool_config: "t1.xml", error_message: "error" },
                        { tool_config: "t2.xml", error_message: "error" },
                        { tool_config: "t3.xml", error_message: "error" },
                        { tool_config: "t4.xml", error_message: "error" },
                        { tool_config: "t5.xml", error_message: "error" },
                    ],
                }),
            }

            const wrapper = mountTab({ metadata: manyInvalidMetadata })

            expect(wrapper.text()).toContain("5 invalid")
            expect(wrapper.find(".invalid-tools-badge").text()).toBe("5 invalid")
        })
    })
})
