import { afterEach, describe, expect, it, onTestFinished } from "vitest"
import { enableAutoUnmount, mount } from "@vue/test-utils"
import { createPinia, disposePinia } from "pinia"
import { useAuthStore, useRepositoryStore } from "@/stores"
import ManagePushAccess from "./ManagePushAccess.vue"

enableAutoUnmount(afterEach)

describe("ManagePushAccess", () => {
    it("shows the repository owner to a non-owner manager", () => {
        const pinia = createPinia()
        onTestFinished(() => disposePinia(pinia))
        const authStore = useAuthStore(pinia)
        const repositoryStore = useRepositoryStore(pinia)
        authStore.user = { username: "iuc" }
        repositoryStore.$patch({
            repository: { owner: "devteam" },
            repositoryPermissions: { can_manage: true, can_push: true, allow_push: ["collaborator"] },
        })

        const wrapper = mount(ManagePushAccess, {
            props: { repositoryId: "repository-id" },
            global: { plugins: [pinia], stubs: { SelectUser: true } },
        })
        const entries = wrapper.findAll(".push-access-owner, .push-access-user")
        expect(entries[0].text()).toBe("devteam (owner)")
        expect(entries[0].find(".push-access-remove").exists()).toBe(false)
        expect(entries[1].text()).toContain("collaborator")
        expect(entries[1].find(".push-access-remove").exists()).toBe(true)
        expect(wrapper.text()).not.toContain("iuc")
    })
})
