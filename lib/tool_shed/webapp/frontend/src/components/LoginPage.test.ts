import { describe, expect, it } from "vitest"
import { mount, RouterLinkStub } from "@vue/test-utils"
import LoginForm from "./LoginForm.vue"
import LoginPage from "./LoginPage.vue"

describe("LoginPage", () => {
    it("passes the return path to the form and the register link", () => {
        const wrapper = mount(LoginPage, {
            props: { returnTo: "/repos/devteam/bismark/shortlog" },
            global: { stubs: { RouterLink: RouterLinkStub } },
        })

        expect(wrapper.getComponent(LoginForm).props("returnTo")).toBe("/repos/devteam/bismark/shortlog")
        expect(wrapper.findAllComponents(RouterLinkStub)[0]!.props("to")).toBe(
            "/register?redirect=%2Frepos%2Fdevteam%2Fbismark%2Fshortlog",
        )
    })
})
