import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";
import UserDeletion from "./UserDeletion";

const localVue = getLocalVue(true);

const TEST_USER_ID = "myTestUserId";
const TEST_EMAIL = `${TEST_USER_ID}@test.com`;
const TEST_ROOT = "/";

function mountComponent() {
    const wrapper = mount(UserDeletion, {
        propsData: { userId: TEST_USER_ID, root: TEST_ROOT, email: TEST_EMAIL },
        localVue,
    });
    return wrapper;
}

import { ROOT_COMPONENT } from "utils/navigation";

describe("UserDeletion.vue", () => {
    it("contains a localized link", async () => {
        const wrapper = mountComponent();
        const el = await wrapper.find(ROOT_COMPONENT.preferences.delete_account.selector);
        expect(el.text()).toBeLocalizationOf("Delete Account");
    });
});
