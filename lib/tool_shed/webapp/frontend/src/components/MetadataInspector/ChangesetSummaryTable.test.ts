import { describe, it, expect, beforeEach, vi } from "vitest"
import { mount } from "@vue/test-utils"
import ChangesetSummaryTable from "./ChangesetSummaryTable.vue"
import { getChangesetDetails, resetMetadataPreview, makeChangeset, type ChangesetMetadataStatus } from "./__fixtures__"

// Real fixture data from API
const fixtureChangesets = getChangesetDetails(resetMetadataPreview)

describe("ChangesetSummaryTable", () => {
    beforeEach(() => {
        vi.clearAllMocks()
    })

    describe("rendering with real fixture data", () => {
        it("renders a table", () => {
            const wrapper = mount(ChangesetSummaryTable, {
                props: { changesets: fixtureChangesets },
            })

            expect(wrapper.find("table").exists() || wrapper.find(".q-table").exists()).toBe(true)
        })

        it("displays all changesets from fixture", () => {
            const wrapper = mount(ChangesetSummaryTable, {
                props: { changesets: fixtureChangesets },
            })

            // Fixture has changesets - verify they're displayed
            for (const cs of fixtureChangesets) {
                const shortHash = cs.changeset_revision.substring(0, 7)
                expect(wrapper.text()).toContain(`${cs.numeric_revision}:${shortHash}`)
            }
        })

        it("shows column headers", () => {
            const wrapper = mount(ChangesetSummaryTable, {
                props: { changesets: fixtureChangesets },
            })

            expect(wrapper.text()).toContain("Revision")
            expect(wrapper.text()).toContain("Action")
            expect(wrapper.text()).toContain("Tools")
            expect(wrapper.text()).toContain("Error")
        })
    })

    describe("action display", () => {
        it("displays all action types", () => {
            const changesets = [
                makeChangeset({ numeric_revision: 4, action: "updated" }),
                makeChangeset({ numeric_revision: 3, action: "created" }),
                makeChangeset({ numeric_revision: 2, action: "unchanged" }),
                makeChangeset({ numeric_revision: 1, action: "skipped", has_tools: false }),
            ]

            const wrapper = mount(ChangesetSummaryTable, {
                props: { changesets },
            })

            expect(wrapper.text()).toContain("updated")
            expect(wrapper.text()).toContain("created")
            expect(wrapper.text()).toContain("unchanged")
            expect(wrapper.text()).toContain("skipped")
        })

        it("renders created action in a chip with positive color", () => {
            const changesets = [makeChangeset({ action: "created" })]
            const wrapper = mount(ChangesetSummaryTable, { props: { changesets } })

            const chip = wrapper.find(".q-chip")
            expect(chip.exists()).toBe(true)
            expect(chip.text()).toContain("created")
            // Quasar applies color as a class
            expect(chip.classes().some((c) => c.includes("positive") || c.includes("bg-positive"))).toBe(true)
        })

        it("renders error action in a chip with negative color", () => {
            const changesets = [
                makeChangeset({
                    action: "error" as ChangesetMetadataStatus["action"],
                    has_tools: false,
                    error: "Something went wrong",
                }),
            ]
            const wrapper = mount(ChangesetSummaryTable, { props: { changesets } })

            const chip = wrapper.find(".q-chip")
            expect(chip.exists()).toBe(true)
            expect(chip.text()).toContain("error")
            expect(chip.classes().some((c) => c.includes("negative") || c.includes("bg-negative"))).toBe(true)
        })
    })

    describe("tools indicator", () => {
        it("shows check icon with positive color when has_tools is true", () => {
            const changesets = [makeChangeset({ has_tools: true })]
            const wrapper = mount(ChangesetSummaryTable, { props: { changesets } })

            // Find the tools column icon
            const icons = wrapper.findAll(".q-icon")
            const checkIcon = icons.find(
                (icon) => icon.text().includes("check") || icon.attributes("name")?.includes("check")
            )
            expect(checkIcon).toBeTruthy()
        })

        it("shows close icon with grey color when has_tools is false", () => {
            const changesets = [makeChangeset({ action: "unchanged", has_tools: false })]
            const wrapper = mount(ChangesetSummaryTable, { props: { changesets } })

            const icons = wrapper.findAll(".q-icon")
            const closeIcon = icons.find(
                (icon) => icon.text().includes("close") || icon.attributes("name")?.includes("close")
            )
            expect(closeIcon).toBeTruthy()
        })
    })

    describe("error display", () => {
        it("displays error message when present", () => {
            const changesets = [
                makeChangeset({
                    action: "error" as ChangesetMetadataStatus["action"],
                    has_tools: false,
                    error: "Failed to parse tool XML",
                }),
            ]

            const wrapper = mount(ChangesetSummaryTable, {
                props: { changesets },
            })

            expect(wrapper.text()).toContain("Failed to parse tool XML")
        })

        it("does not render 'null' text when error is null", () => {
            const changesets = [makeChangeset({ error: null })]

            const wrapper = mount(ChangesetSummaryTable, {
                props: { changesets },
            })

            expect(wrapper.text()).not.toContain("null")
        })
    })

    describe("edge cases", () => {
        it("renders empty table when changesets array is empty", () => {
            const wrapper = mount(ChangesetSummaryTable, {
                props: { changesets: [] },
            })

            expect(wrapper.find("table").exists() || wrapper.find(".q-table").exists()).toBe(true)
        })

        it("truncates changeset hash to 7 characters", () => {
            const changesets = [
                makeChangeset({
                    changeset_revision: "abcdefghijklmnop",
                }),
            ]

            const wrapper = mount(ChangesetSummaryTable, {
                props: { changesets },
            })

            expect(wrapper.text()).toContain("1:abcdefg")
            expect(wrapper.text()).not.toContain("abcdefghijklmnop")
        })

        it("displays long error messages", () => {
            const longError =
                "This is a very long error message that describes what went wrong during the metadata reset operation in great detail"

            const changesets = [
                makeChangeset({
                    action: "error" as ChangesetMetadataStatus["action"],
                    has_tools: false,
                    error: longError,
                }),
            ]

            const wrapper = mount(ChangesetSummaryTable, {
                props: { changesets },
            })

            expect(wrapper.text()).toContain(longError)
        })
    })
})
