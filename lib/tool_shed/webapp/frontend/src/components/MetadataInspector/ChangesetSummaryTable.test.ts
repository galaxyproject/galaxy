import { describe, it, expect, beforeEach, vi } from "vitest"
import { mount } from "@vue/test-utils"
import ChangesetSummaryTable from "./ChangesetSummaryTable.vue"
import { getChangesetDetails, resetMetadataPreview, makeChangeset } from "./__fixtures__"

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
            expect(wrapper.text()).toContain("Change Type")
            expect(wrapper.text()).toContain("Snapshot")
            expect(wrapper.text()).toContain("Tools")
            expect(wrapper.text()).toContain("Error")
        })
    })

    describe("comparison_result display", () => {
        it("displays friendly labels for comparison_result values", () => {
            const changesets = [
                makeChangeset({ comparison_result: "initial", record_operation: null }),
                makeChangeset({ comparison_result: "not equal and not subset", record_operation: "updated" }),
                makeChangeset({ comparison_result: "equal", record_operation: null }),
                makeChangeset({ comparison_result: "subset", record_operation: null }),
            ]

            const wrapper = mount(ChangesetSummaryTable, { props: { changesets } })

            // Check for friendly labels instead of raw API values
            expect(wrapper.text()).toContain("First revision")
            expect(wrapper.text()).toContain("Modified")
            expect(wrapper.text()).toContain("Unchanged")
            expect(wrapper.text()).toContain("Expanded")
        })

        it("shows dash when comparison_result is null", () => {
            const changesets = [makeChangeset({ comparison_result: null, error: "some error" })]
            const wrapper = mount(ChangesetSummaryTable, { props: { changesets } })

            expect(wrapper.text()).toContain("—")
        })
    })

    describe("record_operation display", () => {
        it("displays created in a chip with positive color", () => {
            const changesets = [
                makeChangeset({ comparison_result: "not equal and not subset", record_operation: "created" }),
            ]
            const wrapper = mount(ChangesetSummaryTable, { props: { changesets } })

            const chip = wrapper.find(".q-chip")
            expect(chip.exists()).toBe(true)
            expect(chip.text()).toContain("created")
            expect(chip.classes().some((c) => c.includes("positive") || c.includes("bg-positive"))).toBe(true)
        })

        it("displays updated in a chip with info color", () => {
            const changesets = [
                makeChangeset({ comparison_result: "not equal and not subset", record_operation: "updated" }),
            ]
            const wrapper = mount(ChangesetSummaryTable, { props: { changesets } })

            const chip = wrapper.find(".q-chip")
            expect(chip.exists()).toBe(true)
            expect(chip.text()).toContain("updated")
            expect(chip.classes().some((c) => c.includes("info") || c.includes("bg-info"))).toBe(true)
        })

        it("shows dash when record_operation is null", () => {
            const changesets = [makeChangeset({ comparison_result: "initial", record_operation: null })]
            const wrapper = mount(ChangesetSummaryTable, { props: { changesets } })

            // Should have a dash in the snapshot column
            const cells = wrapper.findAll("td")
            const hasEmDash = cells.some((cell) => cell.text().includes("—"))
            expect(hasEmDash).toBe(true)
        })
    })

    describe("tools indicator", () => {
        it("shows check icon when has_tools is true", () => {
            const changesets = [makeChangeset({ has_tools: true })]
            const wrapper = mount(ChangesetSummaryTable, { props: { changesets } })

            const icons = wrapper.findAll(".q-icon")
            const checkIcon = icons.find(
                (icon) => icon.text().includes("check") || icon.attributes("name")?.includes("check")
            )
            expect(checkIcon).toBeTruthy()
        })

        it("shows close icon when has_tools is false", () => {
            const changesets = [makeChangeset({ has_tools: false })]
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
            const changesets = [makeChangeset({ error: "Failed to parse tool XML" })]
            const wrapper = mount(ChangesetSummaryTable, { props: { changesets } })

            expect(wrapper.text()).toContain("Failed to parse tool XML")
        })

        it("does not render 'null' text when error is null", () => {
            const changesets = [makeChangeset({ error: null })]
            const wrapper = mount(ChangesetSummaryTable, { props: { changesets } })

            expect(wrapper.text()).not.toContain("null")
        })
    })

    describe("edge cases", () => {
        it("renders empty table when changesets array is empty", () => {
            const wrapper = mount(ChangesetSummaryTable, { props: { changesets: [] } })

            expect(wrapper.find("table").exists() || wrapper.find(".q-table").exists()).toBe(true)
        })

        it("truncates changeset hash to 7 characters", () => {
            const changesets = [makeChangeset({ changeset_revision: "abcdefghijklmnop" })]
            const wrapper = mount(ChangesetSummaryTable, { props: { changesets } })

            expect(wrapper.text()).toContain("1:abcdefg")
            expect(wrapper.text()).not.toContain("abcdefghijklmnop")
        })
    })
})
