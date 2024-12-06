import { mount, type Wrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { getLocalVue } from "tests/jest/helpers";

import { generateRandomString } from "./testUtils";

import WorkflowRunButton from "./WorkflowRunButton.vue";

const localVue = getLocalVue();

const WORKFLOW_ID = generateRandomString();
const WORKFLOW_VERSION = 1;
const WORKFLOW_RUN_BUTTON_SELECTOR = `[data-workflow-run="${WORKFLOW_ID}"]`;

function getPath() {
    return `/workflows/run?id=${WORKFLOW_ID}&version=${WORKFLOW_VERSION}`;
}

async function mountWorkflowRunButton(
    props?: { id: string; version: number; full?: boolean; force?: boolean },
    currentPath?: string
) {
    const mockRouter = {
        push: jest.fn(),
        afterEach: jest.fn(),
        currentRoute: {
            fullPath: currentPath || getPath(),
        },
    };

    const wrapper = mount(WorkflowRunButton as object, {
        propsData: { ...props },
        localVue,
        mocks: {
            $router: mockRouter,
        },
    });

    return { wrapper, mockRouter };
}

async function clickButton(button: Wrapper<Vue>) {
    // Remove the href and target attributes to prevent navigation error
    // This is done because the `BButton` has a `:to` prop as well as an `@click` event
    button.element.setAttribute("href", "javascript:void(0)");
    button.element.setAttribute("target", "");

    await button.trigger("click");
    await flushPromises();
}

describe("WorkflowRunButton.vue", () => {
    it("should render button with icon and route to it", async () => {
        const { wrapper, mockRouter } = await mountWorkflowRunButton({ id: WORKFLOW_ID, version: WORKFLOW_VERSION });

        const button = wrapper.find(WORKFLOW_RUN_BUTTON_SELECTOR);
        expect(button.attributes("title")).toBe("Run workflow");
        expect(button.text()).toBe("");
        expect(button.attributes("href")).toBe(getPath());

        await clickButton(button);

        // Check that router.push was called with the correct arguments
        expect(mockRouter.push).toHaveBeenCalledWith(getPath());
    });

    it("should force route if on the same path", async () => {
        const { wrapper, mockRouter } = await mountWorkflowRunButton(
            { id: WORKFLOW_ID, version: WORKFLOW_VERSION, force: true },
            getPath()
        );

        const button = wrapper.find(WORKFLOW_RUN_BUTTON_SELECTOR);

        await clickButton(button);

        // Check that router.push was called with the correct arguments
        expect(mockRouter.push).toHaveBeenCalledWith(getPath(), { force: true });
    });
});
