<template>
    <div v-infinite-scroll="loadMore" infinite-scroll-disabled="busy">
        <b-overlay :show="busy" opacity="0.5">
            <b-table ref="toolTable" striped bordered :fields="fields" :items="buffer">
                <template v-slot:cell(name)="row">
                    <span v-if="!row.item.help_text"
                        ><b>{{ row.item.name }}</b> {{ row.item.description }}</span
                    >
                    <span v-else>
                        <b-link href="javascript:void(0)" role="button" @click="toggleHelp(row)">
                            <b>{{ row.item.name }}</b> {{ row.item.description }}
                        </b-link>
                        <p v-if="!row.item._showDetails && row.item.summary" v-html="row.item.summary" />
                    </span>
                </template>
                <template v-slot:row-details="row">
                    <b-card v-if="row.item.help_text">
                        <p class="mb-1" v-html="row.item.help_text" />
                        <a
                            :href="row.item.target === 'galaxy_main' ? 'javascript:void(0)' : row.item.link"
                            @click.stop="onOpen(row.item)">
                            Click here to open the tool
                        </a>
                    </b-card>
                </template>
                <template v-slot:cell(section)="row">
                    {{ row.item.panel_section_name }}
                </template>
                <template v-slot:cell(workflow)="row">
                    <span
                        v-if="row.item.is_workflow_compatible"
                        v-b-tooltip.hover
                        class="fa fa-check text-success"
                        title="Is Workflow Compatible" />
                    <span v-else v-b-tooltip.hover class="fa fa-times text-danger" title="Not Workflow Compatible" />
                </template>
                <template v-slot:cell(target)="row">
                    <span
                        v-if="row.item.target === 'galaxy_main'"
                        v-b-tooltip.hover
                        class="fa fa-check text-success"
                        title="Is Local" />
                    <span v-else v-b-tooltip.hover class="fa fa-times text-danger" title="Not Local" />
                </template>
                <template v-slot:cell(open)="row">
                    <b-button
                        v-b-tooltip.hover.top
                        :title="'Open Tool' | localize"
                        class="fa fa-play"
                        size="sm"
                        variant="primary"
                        :href="row.item.target === 'galaxy_main' ? 'javascript:void(0)' : row.item.link"
                        @click.stop="onOpen(row.item)" />
                </template>
            </b-table>
        </b-overlay>
    </div>
</template>

<script>
const loadTimeout = 100;
const defaultBufferLen = 4;
import _l from "utils/localization";
import infiniteScroll from "vue-infinite-scroll";
import { openGlobalUploadModal } from "components/Upload";
import { fetchData } from "./services";

export default {
    directives: { infiniteScroll },
    props: {
        tools: {
            type: Array,
            default: null,
        },
    },
    data() {
        return {
            buffer: {},
            bufferLen: defaultBufferLen,
            busy: false,
            fields: [
                {
                    key: "name",
                    label: _l("Name"),
                    sortable: true,
                },
                {
                    key: "section",
                    label: _l("Section"),
                    sortable: true,
                },
                {
                    key: "workflow",
                    label: _l("Workflow Compatible"),
                    sortable: false,
                },
                {
                    key: "target",
                    label: _l("Local Tool"),
                    sortable: false,
                },
                {
                    key: "open",
                    label: "",
                },
            ],
        };
    },
    created() {
        const initData = { summary: "", help_text: "", _showDetails: false, is_fetched: false };
        this.buffer = this.tools.slice(0, this.bufferLen);
        this.buffer.forEach((tool) => Object.assign(tool, { ...initData }));
        this.buffer.forEach(async (tool, index) => {
            await this.fetchHelp(index);
        });
    },
    methods: {
        onOpen(tool) {
            if (tool.id === "upload1") {
                openGlobalUploadModal();
            } else if (tool.form_style === "regular") {
                // encode spaces in tool.id
                const toolId = tool.id;
                const toolVersion = tool.version;
                this.$router.push({ path: `/?tool_id=${encodeURIComponent(toolId)}&version=${toolVersion}` });
            }
        },
        async loadMore() {
            if (this.buffer.length < this.tools.length) {
                this.busy = true;
                setTimeout(() => {
                    this.bufferLen += defaultBufferLen;
                    this.buffer = this.tools.slice(0, this.bufferLen);
                    this.buffer.forEach(async (tool, index) => {
                        await this.fetchHelp(index);
                    });
                    this.busy = false;
                }, loadTimeout);
            }
        },
        toggleHelp(row) {
            row.toggleDetails();
            this.$refs.toolTable.refresh();
        },
        async fetchHelp(index) {
            const id = this.buffer[index]["id"];
            if (!this.buffer[index]["is_fetched"]) {
                this.buffer[index]["is_fetched"] = true; // tags the tool's help as being fetched
                await fetchData(`api/tools/${id}/build`).then((response) => {
                    if (response.help && response.help != "\n") {
                        this.buffer[index]["help_text"] = response.help;
                        this.buffer[index]["summary"] = this.parseHelp(response.help);
                    } else {
                        this.buffer[index]["help_text"] = ""; // for cases where helpText == '\n'
                    }
                });
                this.$refs.toolTable.refresh();
            }
        },
        parseHelp(help) {
            let summary = "";
            const parser = new DOMParser();
            const helpDoc = parser.parseFromString(help, "text/html");
            const xpaths = [
                "//strong[text()='What it does']/../following-sibling::*",
                "//strong[text()='What It Does']/../following-sibling::*",
                "//h1[text()='Synopsis']/following-sibling::*",
                "//strong[text()='Syntax']/../following-sibling::*",
            ];
            const matches = [];
            xpaths.forEach((xpath) => {
                matches.push(
                    helpDoc.evaluate(xpath, helpDoc, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue
                );
            });
            matches.forEach((match) => {
                if (match) {
                    summary += match.innerHTML + "\n";
                }
            });
            return summary;
        },
    },
};
</script>
