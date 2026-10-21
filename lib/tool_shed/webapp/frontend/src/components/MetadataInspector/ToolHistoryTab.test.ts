import { afterEach, describe, it, expect } from "vitest"
import { enableAutoUnmount, mount } from "@vue/test-utils"
import ToolHistoryTab from "./ToolHistoryTab.vue"
import {
    repositoryMetadataColumnMaker,
    simulatedMetadataMultiTool,
    simulatedMetadataEmpty,
    makeRevision,
    makeTool,
    type RepositoryMetadata,
} from "./__fixtures__"

import { MetadataJsonViewerStub } from "./test-utils"

enableAutoUnmount(afterEach)

const fixtureMetadata = repositoryMetadataColumnMaker

function mountTab(props: { metadata: RepositoryMetadata | null }) {
    return mount(ToolHistoryTab, {
        props,
        global: { stubs: { MetadataJsonViewer: MetadataJsonViewerStub } },
    })
}

describe("ToolHistoryTab", () => {
    describe("rendering", () => {
        it("displays 'No tools found' when metadata is null", () => {
            const wrapper = mountTab({ metadata: null })

            expect(wrapper.text()).toContain("No tools found")
        })

        it("displays 'No tools found' when metadata has no tools", () => {
            const wrapper = mountTab({ metadata: simulatedMetadataEmpty })

            expect(wrapper.text()).toContain("No tools found")
        })

        it("displays tool cards with tool ID as header", () => {
            const wrapper = mountTab({ metadata: fixtureMetadata })

            const cards = wrapper.findAll(".tool-history-card")
            expect(cards).toHaveLength(1)
            expect(wrapper.text()).toContain("Add_a_column1")
        })

        it("shows version numbers in timeline", () => {
            const wrapper = mountTab({ metadata: fixtureMetadata })

            expect(wrapper.findAll(".tool-history-version").map((version) => version.text())).toEqual([
                "1.3.0",
                "1.2.0",
                "1.1.0",
            ])
        })
    })

    describe("revision badge", () => {
        it("labels each version with its revision number", () => {
            const wrapper = mountTab({ metadata: fixtureMetadata })

            const badges = wrapper.findAll(".revision-badge")
            expect(badges.map((badge) => badge.text())).toEqual(["[2]", "[1]", "[0]"])
        })
    })

    describe("timeline", () => {
        it("lists each tool's versions as an ordered list with name and description", () => {
            const wrapper = mountTab({ metadata: simulatedMetadataMultiTool })

            const timelines = wrapper.findAll("ol.tool-history-timeline")
            expect(timelines.length).toBe(4)

            const entries = wrapper.findAll("li.tool-history-entry")
            expect(entries).toHaveLength(10)
            expect(entries[0].find(".tool-history-subtitle").text()).toBe(
                "Sequence Aligner Align sequences using algorithm A - performance optimized",
            )
        })
    })

    describe("tool history sorting", () => {
        it("sorts versions with newest revision first", () => {
            const wrapper = mountTab({ metadata: fixtureMetadata })

            expect(wrapper.findAll(".tool-history-version").map((version) => version.text())).toEqual([
                "1.3.0",
                "1.2.0",
                "1.1.0",
            ])
        })

        it("sorts tools alphabetically by tool ID", () => {
            const wrapper = mountTab({ metadata: simulatedMetadataMultiTool })

            expect(wrapper.findAll(".tool-history-card-title").map((title) => title.text())).toEqual([
                "align_sequences",
                "convert_format",
                "filter_quality",
                "merge_sequences",
            ])
        })
    })

    describe("events", () => {
        it("emits goToRevision when revision link is clicked", async () => {
            const wrapper = mountTab({ metadata: fixtureMetadata })

            const revisionButton = wrapper.get(".tool-history-title-row button")
            expect(revisionButton.text()).toBe("Rev 2")

            await revisionButton.trigger("click")

            expect(wrapper.emitted("goToRevision")).toEqual([["2:062143ff0665"]])
        })
    })

    describe("expansion", () => {
        it("has expandable tool details section", () => {
            const wrapper = mountTab({ metadata: fixtureMetadata })

            const toggles = wrapper.findAll(".tool-details-toggle")
            expect(toggles).toHaveLength(3)
        })

        it("toggles tool details from an accessible button", async () => {
            const wrapper = mountTab({ metadata: fixtureMetadata })

            const toggle = wrapper.find(".tool-details-toggle")
            expect(toggle.element.tagName).toBe("BUTTON")
            expect(toggle.text()).toContain("Tool Details")
            expect(toggle.attributes("aria-expanded")).toBe("false")

            const details = wrapper.find(`#${toggle.attributes("aria-controls")}`)
            expect(details.exists()).toBe(true)
            expect(details.find(".mock-json-viewer").exists()).toBe(false)

            await toggle.trigger("click")

            expect(toggle.attributes("aria-expanded")).toBe("true")
            expect(details.find(".mock-json-viewer").exists()).toBe(true)
            expect(wrapper.findAll(".tool-details-toggle[aria-expanded=true]").length).toBe(1)

            await toggle.trigger("click")

            expect(toggle.attributes("aria-expanded")).toBe("false")
        })
    })

    describe("edge cases", () => {
        it("shows multiple entries when tool has same version in different revisions", () => {
            // simulatedMetadataMultiTool has filter_quality at 1.0.0 in rev 0 and rev 1
            const wrapper = mountTab({ metadata: simulatedMetadataMultiTool })

            const [qualityFilter] = wrapper
                .findAll(".tool-history-card")
                .filter((card) => card.get(".tool-history-card-title").text() === "filter_quality")
            expect(qualityFilter.findAll(".tool-history-version").map((version) => version.text())).toEqual([
                "1.1.0",
                "1.0.0",
                "1.0.0",
            ])
            expect(qualityFilter.findAll(".revision-badge").map((badge) => badge.text())).toEqual(["[2]", "[1]", "[0]"])
        })

        it("handles special characters in tool IDs", () => {
            const specialCharsMetadata: RepositoryMetadata = {
                "0:specialchars": makeRevision({
                    tools: [makeTool({ id: "tool_with-special.chars", name: "Tool Name", version: "1.0" })],
                }),
            }

            const wrapper = mountTab({ metadata: specialCharsMetadata })

            expect(wrapper.text()).toContain("tool_with-special.chars")
        })
    })
})
