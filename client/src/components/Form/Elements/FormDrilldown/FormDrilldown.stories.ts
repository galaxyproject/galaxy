import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { withModel } from "@tests/test-data/withModel";
import { expect, waitFor } from "storybook/test";
import { h } from "vue";

import { getAllValues, type Option } from "./utilities";

import FormDrilldown from "./FormDrilldown.vue";

export const FormDrilldownWithModel = withModel(FormDrilldown, "FormDrilldownWithModel");

/** A tree of options where any node, not only a leaf, can be picked: a tool's `drill_down` parameter or a library directory picker. */
const meta = {
    title: "Form/Elements/FormDrilldown",
    component: FormDrilldown,
    excludeStories: ["FormDrilldownWithModel"],
    render: (args) => () => h(FormDrilldownWithModel, args),
    args: {
        id: "taxonomy",
        multiple: true,
        options: [
            {
                name: "Bacteria",
                value: "bacteria",
                options: [
                    { name: "Firmicutes", value: "firmicutes", options: [] },
                    {
                        name: "Proteobacteria",
                        value: "proteobacteria",
                        options: [{ name: "Escherichia", value: "escherichia", options: [] }],
                    },
                ],
            },
            {
                name: "Archaea",
                value: "archaea",
                options: [{ name: "Euryarchaeota", value: "euryarchaeota", options: [] }],
            },
        ],
    },
} satisfies Meta<typeof FormDrilldown>;

export default meta;
type Story = StoryObj<typeof meta>;

type PlayContext = Parameters<NonNullable<Story["play"]>>[0];

function optionNames(options: Option[]): string[] {
    return options.flatMap((option) => [option.name, ...optionNames(option.options)]);
}

const ALL = optionNames(meta.args.options);
const ALL_VALUES = getAllValues(meta.args.options);

/** Options are checkboxes, or radio buttons when not `multiple`. */
type Role = "checkbox" | "radio";

/**
 * Opens an option's children with the caret beside it, checking they were hidden before.
 * Pre-existing bug, worked around here: the caret is an icon-only button with no name, so it's
 * found beside its option (BUGS_FOUND).
 */
async function expand({ canvas, step, userEvent }: PlayContext, role: Role, name: string, firstChild: string) {
    await step(`Open "${name}"`, async () => {
        // Bootstrap's custom inputs are transparent, so check the child's label.
        await expect(canvas.getByText(firstChild)).not.toBeVisible();
        const caret = canvas.getByRole(role, { name }).parentElement!.previousElementSibling as HTMLElement;
        await userEvent.click(caret);
        await expect(canvas.getByText(firstChild)).toBeVisible();
    });
}

async function pick({ canvas, step, userEvent }: PlayContext, name: string) {
    await step(`Click "${name}"`, async () => {
        await userEvent.click(canvas.getByText(name));
    });
}

/** Checks which of the shown options are ticked: exactly `ticked`, in any order. */
async function seeTicked({ canvas, step }: PlayContext, role: Role, ticked: string[]) {
    await step(`See ticked: ${ticked.join(", ") || "nothing"}`, async () => {
        await waitFor(async () => {
            const shown = ALL.filter((name) => canvas.queryByRole(role, { name }));
            await expect(shown).not.toHaveLength(0);
            for (const name of shown) {
                const option = canvas.getByRole(role, { name });
                await (ticked.includes(name) ? expect(option).toBeChecked() : expect(option).not.toBeChecked());
            }
            await expect(shown).toEqual(expect.arrayContaining(ticked));
        });
    });
}

/** Checks the select-all box, which follows how many options are ticked. */
async function seeSelectAll({ canvas, step }: PlayContext, state: "unticked" | "partly ticked" | "ticked") {
    await step(`See "Select / Deselect All" ${state}`, async () => {
        const selectAll = canvas.getByRole("checkbox", { name: "Select / Deselect All" });
        await waitFor(async () => {
            await (state === "partly ticked"
                ? expect(selectAll).toBePartiallyChecked()
                : expect(selectAll).not.toBePartiallyChecked());
            await (state === "ticked" ? expect(selectAll).toBeChecked() : expect(selectAll).not.toBeChecked());
        });
    });
}

export const NothingSelected: Story = { args: { value: [] } };

/** Ticking an option with children ticks only that option; its children stay unticked. */
export const TicksOnlyTheChosenOption: Story = {
    ...NothingSelected,
    play: async (context) => {
        await seeSelectAll(context, "unticked");
        await seeTicked(context, "checkbox", []);
        await pick(context, "Bacteria");
        await seeSelectAll(context, "partly ticked");
        await expand(context, "checkbox", "Bacteria", "Firmicutes");
        await seeTicked(context, "checkbox", ["Bacteria"]);
    },
};

/** A selected option opens its parent, so it is in view. */
export const NestedOptionSelected: Story = { args: { value: ["euryarchaeota"] } };

/**
 * Ticking the last unticked option keeps every other one ticked, so select-all ticks too. Starts
 * with all but one ticked, so select-all shows the update; selected children keep their parents open.
 */
export const KeepsOtherSelections: Story = {
    args: { value: ALL_VALUES.filter((value) => value !== "proteobacteria") },
    play: async (context) => {
        await seeSelectAll(context, "partly ticked");
        await seeTicked(
            context,
            "checkbox",
            ALL.filter((name) => name !== "Proteobacteria"),
        );
        await pick(context, "Proteobacteria");
        await seeSelectAll(context, "ticked");
        await seeTicked(context, "checkbox", ALL);
    },
};

/** A parent and one of its children ticked separately: the form submits only what was picked, so ticking a parent leaves its children unticked. */
export const ParentAndChildSelected: Story = { args: { value: ["bacteria", "firmicutes"] } };

/** Unticking a parent leaves its ticked children ticked. Starts with everything ticked, so select-all shows the update. */
export const KeepsTickedChildren: Story = {
    args: { value: ALL_VALUES },
    play: async (context) => {
        await seeSelectAll(context, "ticked");
        await seeTicked(context, "checkbox", ALL);
        await pick(context, "Bacteria");
        await seeSelectAll(context, "partly ticked");
        await seeTicked(
            context,
            "checkbox",
            ALL.filter((name) => name !== "Bacteria"),
        );
    },
};

/** Not multiple: radio buttons pick one option. */
export const SingleChoice: Story = { args: { multiple: false, value: null } };

/** Picking an option replaces the one picked before. */
export const PicksOneOption: Story = {
    ...SingleChoice,
    play: async (context) => {
        await expand(context, "radio", "Bacteria", "Firmicutes");
        await context.step("See no select-all box", async () => {
            await expect(context.canvas.queryByRole("checkbox")).not.toBeInTheDocument();
        });
        await expand(context, "radio", "Proteobacteria", "Escherichia");
        await pick(context, "Escherichia");
        await seeTicked(context, "radio", ["Escherichia"]);
        await pick(context, "Firmicutes");
        await seeTicked(context, "radio", ["Firmicutes"]);
    },
};

export const NoOptions: Story = { args: { options: [], value: [] } };
