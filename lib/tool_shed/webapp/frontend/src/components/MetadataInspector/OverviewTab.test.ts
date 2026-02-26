import { describe, it, expect, beforeEach, vi } from "vitest"
import { mount } from "@vue/test-utils"
import OverviewTab from "./OverviewTab.vue"
import { repositoryMetadataColumnMaker, makeRevision, type RepositoryMetadata } from "./__fixtures__"

vi.mock("./MetadataJsonViewer.vue", () => ({
    default: {
        name: "MetadataJsonViewer",
        props: ["data", "modelName", "deep"],
        template: '<div class="mock-json-viewer">{{ JSON.stringify(data) }}</div>',
    },
}))

const fixtureMetadata = repositoryMetadataColumnMaker

describe("OverviewTab", () => {
    beforeEach(() => {
        vi.clearAllMocks()
    })

    describe("rendering", () => {
        it("displays revision selector when metadata is provided", () => {
            const wrapper = mount(OverviewTab, {
                props: { metadata: fixtureMetadata },
            })

            expect(wrapper.find(".q-select").exists()).toBe(true)
        })

        it("shows 'No metadata available' when metadata is null", () => {
            const wrapper = mount(OverviewTab, {
                props: { metadata: null },
            })

            expect(wrapper.text()).toContain("No metadata available")
        })

        it("shows 'No metadata available' when metadata is empty object", () => {
            const wrapper = mount(OverviewTab, {
                props: { metadata: {} as RepositoryMetadata },
            })

            expect(wrapper.text()).toContain("No metadata available")
        })

        it("displays MetadataJsonViewer with selected revision data", () => {
            const wrapper = mount(OverviewTab, {
                props: { metadata: fixtureMetadata },
            })

            expect(wrapper.find(".mock-json-viewer").exists()).toBe(true)
            // Verify actual data is passed - fixture contains Add_a_column1 tool
            expect(wrapper.find(".mock-json-viewer").text()).toContain("Add_a_column1")
        })
    })

    describe("revision selection", () => {
        it("defaults to newest revision (highest numeric_revision)", () => {
            const wrapper = mount(OverviewTab, {
                props: { metadata: fixtureMetadata },
            })

            // The mock renders JSON - newest revision should have highest version tool
            const viewerText = wrapper.find(".mock-json-viewer").text()
            // column_maker fixture has versions 1.1.0, 1.2.0, 1.3.0 across revisions
            // Newest should show 1.3.0
            expect(viewerText).toContain("1.3.0")
        })
    })

    describe("edge cases", () => {
        it("handles single revision metadata", () => {
            const keys = Object.keys(fixtureMetadata)
            const singleRevision: RepositoryMetadata = {
                [keys[0]]: fixtureMetadata[keys[0]],
            }

            const wrapper = mount(OverviewTab, {
                props: { metadata: singleRevision },
            })

            expect(wrapper.find(".mock-json-viewer").exists()).toBe(true)
        })

        it("handles revision with empty tools array", () => {
            const keys = Object.keys(fixtureMetadata)
            const emptyToolsMetadata: RepositoryMetadata = {
                [keys[0]]: makeRevision({ tools: [] }),
            }

            const wrapper = mount(OverviewTab, {
                props: { metadata: emptyToolsMetadata },
            })

            expect(wrapper.find(".mock-json-viewer").exists()).toBe(true)
        })
    })
})
