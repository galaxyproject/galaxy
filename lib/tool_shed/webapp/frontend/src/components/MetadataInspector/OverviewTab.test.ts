import { afterEach, describe, it, expect } from "vitest"
import { enableAutoUnmount, mount } from "@vue/test-utils"
import OverviewTab from "./OverviewTab.vue"
import { repositoryMetadataColumnMaker, makeRevision, type RepositoryMetadata } from "./__fixtures__"

import { MetadataJsonViewerStub } from "./test-utils"

enableAutoUnmount(afterEach)

function mountTab(metadata: RepositoryMetadata | null) {
    return mount(OverviewTab, {
        props: { metadata },
        global: { stubs: { MetadataJsonViewer: MetadataJsonViewerStub } },
    })
}

describe("OverviewTab", () => {
    describe("rendering", () => {
        it("displays revision selector when metadata is provided", () => {
            const wrapper = mountTab(repositoryMetadataColumnMaker)

            expect(wrapper.find(".q-select").exists()).toBe(true)
        })

        it.each([
            { name: "null", metadata: null },
            { name: "empty", metadata: {} },
        ])("shows 'No metadata available' for $name metadata", ({ metadata }) => {
            const wrapper = mountTab(metadata)

            expect(wrapper.text()).toContain("No metadata available")
        })

        it("displays MetadataJsonViewer with selected revision data", () => {
            const wrapper = mountTab(repositoryMetadataColumnMaker)

            expect(wrapper.find(".mock-json-viewer").exists()).toBe(true)
            // Verify actual data is passed - fixture contains Add_a_column1 tool
            expect(wrapper.find(".mock-json-viewer").text()).toContain("Add_a_column1")
        })
    })

    describe("revision selection", () => {
        it("defaults to newest revision (highest numeric_revision)", () => {
            const wrapper = mountTab(repositoryMetadataColumnMaker)

            const viewer = wrapper.getComponent(MetadataJsonViewerStub)

            expect(viewer.props("data")).toEqual(repositoryMetadataColumnMaker["2:062143ff0665"])
            expect(viewer.text()).toContain("1.3.0")
        })
    })

    describe("edge cases", () => {
        it("handles single revision metadata", () => {
            const singleRevision: RepositoryMetadata = {
                "0:d6e73113c7a5": repositoryMetadataColumnMaker["0:d6e73113c7a5"],
            }

            const wrapper = mountTab(singleRevision)

            expect(wrapper.find(".mock-json-viewer").exists()).toBe(true)
        })

        it("handles revision with empty tools array", () => {
            const emptyToolsMetadata: RepositoryMetadata = {
                "0:d6e73113c7a5": makeRevision({ tools: [] }),
            }

            const wrapper = mountTab(emptyToolsMetadata)

            expect(wrapper.find(".mock-json-viewer").exists()).toBe(true)
        })
    })
})
