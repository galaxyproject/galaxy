<template>
    <span>
        <b-dropdown
            v-for="(categoryName, categoryKey) in categoryNames"
            :key="categoryKey"
            no-caret
            right
            role="button"
            variant="link"
            :title="categoryName.title"
            v-b-tooltip.hover.bottom
        >
            <template v-slot:button-content>
                <span :class="['fa', categoryName.icon]" />
            </template>
            <b-dropdown-item
                v-for="argumentName in categories[categoryKey]"
                :key="argumentName"
                href="#"
                @click="onDropdownClick(argumentName)"
            >
                <span :class="['fa fa-fw mr-1', icons[argumentName]]" />
                {{ titles[argumentName] }}
            </b-dropdown-item>
        </b-dropdown>
        <MarkdownDialog
            v-if="selectedShow"
            :argument-type="selectedType"
            :argument-name="selectedArgumentName"
            :labels="selectedLabels"
            :use-labels="useLabels"
            @onInsert="onInsert"
            @onCancel="onCancel"
        />
    </span>
</template>

<script>
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import MarkdownDialog from "./MarkdownDialog";

Vue.use(BootstrapVue);

export default {
    components: {
        MarkdownDialog,
    },
    props: {
        validArguments: {
            type: Object,
            default: null,
        },
        nodes: {
            type: Object,
            default: null,
        },
    },
    data() {
        return {
            categories: {},
            categoryNames: {
                history_dataset: {
                    title: "Insert Datasets",
                    icon: "fa-file",
                },
                tool: {
                    title: "Insert Jobs",
                    icon: "fa-wrench",
                },
                workflow: {
                    title: "Insert Workflows",
                    icon: "fa-sitemap fa-rotate-270",
                },
                others: {
                    title: "Insert Others",
                    icon: "fa-tools",
                },
            },
            categoryKeys: {
                history_dataset_: "history_dataset",
                history_dataset_collection_: "history_dataset",
                tool_: "tool",
                job_: "tool",
                invocation_: "workflow",
                workflow_: "workflow",
            },
            icons: {
                history_dataset_display: "fa-file-o",
                history_dataset_collection_display: "fa-folder-o",
                history_dataset_as_image: "fa-image",
                history_dataset_link: "fa-link",
                history_dataset_info: "fa-info",
                invocation_time: "fa-clock",
                tool_stderr: "fa-bug",
                tool_stdout: "fa-quote-right",
                job_metrics: "fa-tachometer-alt",
                job_parameters: "fa-tasks",
                generate_time: "fa-stopwatch",
                history_dataset_name: "fa-signature",
                invocation_inputs: "fa-arrow-right",
                invocation_outputs: "fa-arrow-left",
                generate_galaxy_version: "fa-certificate",
                workflow_display: "fa-sitemap fa-rotate-270",
            },
            selectorConfig: {
                job_id: {
                    labelTitle: "Select Step Label",
                    selectTitle: "Select Job by Identifier",
                },
                invocation_id: {
                    labelTitle: "Select Step Label",
                    selectTitle: "Select Invocation by Identifier",
                },
                history_dataset_id: {
                    labelTitle: "Select Output Label",
                    selectTitle: "Select Dataset from History",
                },
                history_dataset_collection_id: {
                    labelTitle: "Select Output Label",
                    selectTitle: "Select Dataset Collection from History",
                },
            },
            titles: {},
            selectedArgumentName: null,
            selectedType: null,
            selectedLabels: null,
            selectedShow: false,
        };
    },
    computed: {
        useLabels() {
            return !!this.nodes;
        },
    },
    created() {
        for (const argumentName in this.validArguments) {
            let categoryName = "";
            for (const categoryKey in this.categoryKeys) {
                if (argumentName.startsWith(categoryKey)) {
                    categoryName = this.categoryKeys[categoryKey];
                    break;
                }
            }
            if (!categoryName) {
                categoryName = "others";
            }
            this.categories[categoryName] = this.categories[categoryName] || [];
            this.categories[categoryName].push(argumentName);
            this.titles[argumentName] = this.getArgumentTitle(argumentName);
        }
        for (const categoryName in this.categories) {
            this.categories[categoryName] = this.categories[categoryName].sort();
        }
    },
    methods: {
        getSteps() {
            const steps = [];
            this.nodes &&
                Object.values(this.nodes).forEach((node) => {
                    if (node.label) {
                        steps.push(node.label);
                    }
                });
            return steps;
        },
        getOutputs() {
            const outputLabels = [];
            this.nodes &&
                Object.values(this.nodes).forEach((node) => {
                    node.outputs.forEach((output) => {
                        if (output.activeLabel) {
                            outputLabels.push(output.activeLabel);
                        }
                    });
                });
            return outputLabels;
        },
        getArgumentTitle(argumentName) {
            return (
                argumentName[0].toUpperCase() +
                argumentName.substr(1).replace(/_([a-z])/g, (g) => {
                    return ` ${g[1].toUpperCase()}`;
                })
            );
        },
        onInsert(markdownBlock) {
            this.$emit("onInsert", markdownBlock);
            this.selectedShow = false;
        },
        onCancel() {
            this.selectedShow = false;
        },
        onDropdownClick(argumentName) {
            this.selectedArgumentName = argumentName;
            const arg = this.validArguments[argumentName];
            if (arg.length == 0) {
                this.$emit("onInsert", `${argumentName}()`);
            } else if (arg.includes("workflow_id")) {
                this.selectedType = "workflow_id";
                this.selectedShow = true;
            } else if (arg.includes("job_id")) {
                this.selectedType = "job_id";
                this.selectedLabels = this.getSteps();
                this.selectedShow = true;
            } else if (arg.includes("invocation_id")) {
                this.selectedType = "invocation_id";
                this.selectedLabels = this.getSteps();
                this.selectedShow = true;
            } else if (arg.includes("history_dataset_id")) {
                this.selectedType = "history_dataset_id";
                this.selectedLabels = this.getOutputs();
                this.selectedShow = true;
            } else if (arg.includes("history_dataset_collection_id")) {
                this.selectedType = "history_dataset_collection_id";
                this.selectedLabels = this.getOutputs();
                this.selectedShow = true;
            } else {
                this.$emit("onInsert", `${argumentName}(${arg.join(", ")}=<ENTER A VALUE>)`);
            }
        },
    },
};
</script>
