import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { withModel } from "@tests/test-data/withModel";
import { h } from "vue";

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

export const NothingSelected: Story = { args: { value: [] } };

/** A selected option opens its parent, so it is in view. */
export const NestedOptionSelected: Story = { args: { value: ["euryarchaeota"] } };

/** A parent and one of its children ticked separately: the form submits only what was picked, so ticking a parent leaves its children unticked. */
export const ParentAndChildSelected: Story = { args: { value: ["bacteria", "firmicutes"] } };

/** Not multiple: radio buttons pick one option. */
export const SingleChoice: Story = { args: { multiple: false, value: null } };

export const NoOptions: Story = { args: { options: [], value: [] } };
