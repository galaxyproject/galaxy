import { beforeEach, describe, expect, it } from "vitest"
import { mount } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import { useAuthStore, useRepositoryStore } from "@/stores"
import ManagePushAccess from "./ManagePushAccess.vue"

describe("ManagePushAccess", () => {
    beforeEach(() => {
        setActivePinia(createPinia())
    })

    it("shows the repository owner to a non-owner manager", () => {
        useAuthStore().user = { username: "iuc" }
        useRepositoryStore().$patch({
            repository: { owner: "devteam" },
            repositoryPermissions: { can_manage: true, can_push: true, allow_push: ["collaborator"] },
        })

        const wrapper = mount(ManagePushAccess, {
            props: { repositoryId: "repository-id" },
            global: { stubs: { SelectUser: true } },
        })
        const entries = wrapper.findAll(".q-item")
        expect(entries[0].text()).toBe("devteam (owner)")
        expect(entries[0].find(".q-icon").exists()).toBe(false)
        expect(entries[1].text()).toContain("collaborator")
        expect(entries[1].find(".q-icon").exists()).toBe(true)
        expect(wrapper.text()).not.toContain("iuc")
    })
})
