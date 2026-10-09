import type { StoryContext } from "@storybook/vue3-vite";
import { expect, waitFor, within } from "storybook/test";

/** What the `vue-multiselect` play helpers need from a play's context. */
type PickerContext = Pick<StoryContext, "canvas" | "userEvent">;

/** Opens the story's one option list, unless it is already open, and returns it once it has faded in. */
export async function openOptions({ canvas, userEvent }: PickerContext) {
    const picker = await canvas.findByRole("combobox");
    if (picker.getAttribute("aria-expanded") !== "true") {
        await userEvent.click(picker);
    }
    const list = await canvas.findByRole("listbox");
    await waitFor(() => expect(list).toBeVisible());
    return list;
}

/**
 * Opens the option list and checks every option offered, in order, and which of them are selected;
 * `{ anyOf }` accepts any one of several selections, to tolerate a known bug.
 */
export async function expectOptions(
    context: PickerContext,
    offered: string[],
    selected: string[] | { anyOf: string[][] },
) {
    const list = await openOptions(context);
    await waitFor(() => {
        const options = within(list).getAllByRole("option");
        expect(options.map((option) => option.textContent?.trim())).toEqual(offered);
        const shown = options
            .filter((option) => option.getAttribute("aria-selected") === "true")
            .map((o) => o.textContent?.trim());
        if (Array.isArray(selected)) {
            expect(shown).toEqual(selected);
        } else {
            expect(selected.anyOf).toContainEqual(shown);
        }
    });
}

/** Opens the option list and clicks the option labelled `label`. */
export async function pickOption(context: PickerContext, label: string) {
    const list = await openOptions(context);
    const option = within(list)
        .getAllByRole("option")
        .find((candidate) => candidate.textContent?.trim() === label);
    if (!option) {
        throw new Error(`No option labelled "${label}".`);
    }
    await context.userEvent.click(within(option).getByText(label));
}
