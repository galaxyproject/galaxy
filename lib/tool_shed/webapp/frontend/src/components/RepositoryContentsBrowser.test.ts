import { mount } from "@vue/test-utils"
import { describe, expect, it } from "vitest"
import { defineComponent, h } from "vue"
import type { RepositoryFileEntry } from "@/api"
import { repositoryMetadataColumnMaker } from "@/components/MetadataInspector/__fixtures__"
import RepositoryContentsBrowser from "./RepositoryContentsBrowser.vue"

// Quasar's select isn't the subject here: let tests pick a revision
const RevisionSelectStub = defineComponent({
    props: { revisions: { type: Object, required: true }, modelValue: { type: String, default: "" } },
    emits: ["update:modelValue"],
    setup(_props, { emit }) {
        return () => h("button", { class: "pick-revision", onClick: () => emit("update:modelValue", "def456") })
    },
})

const files: RepositoryFileEntry[] = [{ path: "column_maker.xml", size: 10, type: "file", executable: false }]

function mountBrowser(props: Record<string, unknown> = {}) {
    return mount(RepositoryContentsBrowser, {
        props: { revisions: repositoryMetadataColumnMaker, revision: "abc123", files, contents: null, ...props },
        global: { stubs: { RevisionSelect: RevisionSelectStub } },
    })
}

describe("RepositoryContentsBrowser", () => {
    it("emits a picked revision and file instead of routing", async () => {
        const wrapper = mountBrowser()

        await wrapper.get(".pick-revision").trigger("click")
        await wrapper.get('nav[aria-label="Files"] button').trigger("click")

        expect(wrapper.emitted("update:revision")).toEqual([["def456"]])
        expect(wrapper.emitted("select")).toEqual([["column_maker.xml"]])
    })

    it("shows only the withdrawn notice for a deprecated repository", () => {
        const wrapper = mountBrowser({ withdrawn: "deprecated" })

        expect(wrapper.text()).toContain("This repository has been deprecated, so its files can't be browsed.")
        expect(wrapper.find(".pick-revision").exists()).toBe(false)
        expect(wrapper.find('nav[aria-label="Files"]').exists()).toBe(false)
    })
})
