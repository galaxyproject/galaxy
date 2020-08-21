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
                @click="onInsert(argumentName)"
            >
                <span :class="['fa fa-fw mr-1', icons[argumentName]]" />
                {{
                    argumentName[0].toUpperCase() +
                    argumentName.substr(1).replace(/_([a-z])/g, (g) => {
                        return ` ${g[1].toUpperCase()}`;
                    })
                }}
            </b-dropdown-item>
        </b-dropdown>
    </span>
</template>

<script>
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import { showMarkdownHelp } from "./markdownHelp";

Vue.use(BootstrapVue);

import { dialog, datasetCollectionDialog, workflowDialog } from "utils/data";

export default {
    props: {
        validArguments: {
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
        };
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
        }
        for (const categoryName in this.categories) {
            this.categories[categoryName] = this.categories[categoryName].sort();
        }
    },
    methods: {
        onInsert(argumentName) {
        },
        selectDataset(galaxyCall) {
            dialog(
                (response) => {
                    const datasetId = response.id;
                    this.$emit("onInsert", `${galaxyCall}(history_dataset_id=${datasetId})`);
                },
                {
                    multiple: false,
                    format: null,
                    library: false, // TODO: support?
                }
            );
        },
        selectDatasetCollection(galaxyCall) {
            datasetCollectionDialog((response) => {
                this.$emit("onInsert", `${galaxyCall}(history_dataset_collection_id=${response.id})`);
            }, {});
        },
        selectWorkflow(galaxyCall) {
            workflowDialog((response) => {
                this.$emit("onInsert", `${galaxyCall}(workflow_display(workflow_id=${response.id})`);
            }, {});
        },
    },
};
</script>
