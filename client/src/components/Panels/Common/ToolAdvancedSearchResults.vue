<template>
    <div v-infinite-scroll="loadMore" infinite-scroll-disabled="busy">
        <b-card v-for="(tool, key) in buffer" :key="key" :class="!listView && 'mb-3'" no-body>
            <b-card-header>
                <span class="d-inline-flex">
                    <span class="d-flex">
                        <a
                            :href="tool.target === 'galaxy_main' ? 'javascript:void(0)' : tool.link"
                            @click.stop="onOpen(tool)">
                            <b>{{ tool.name }}</b> {{ tool.description }}
                        </a>
                        <b-badge class="ml-1">{{ tool.panel_section_name }}</b-badge>
                        <b-badge
                            v-if="tool.is_workflow_compatible"
                            v-b-tooltip.hover
                            class="ml-1"
                            variant="success"
                            title="Can use this tool in Workflows">
                            Workflow
                        </b-badge>
                        <b-badge v-if="tool.hidden" class="ml-1" variant="danger">Hidden</b-badge>
                    </span>
                </span>
            </b-card-header>
            <b-card-body v-if="!listView">
                <span v-if="helpContents[key]['help_text']">
                    <span v-if="helpContents[key]['summary']">
                        <p v-if="!helpContents[key]['toggle_help']" v-html="helpContents[key]['summary']" />
                        <a href="javascript:void(0)" @click.stop="toggleHelp(key)">
                            See
                            <span v-if="!helpContents[key]['toggle_help']">more</span><span v-else>less</span>
                            ...
                        </a>
                    </span>
                    <p v-if="helpContents[key]['toggle_help']" v-html="helpContents[key]['help_text']" />
                </span>
                <i v-else class="text-secondary">There is no information for this tool. Open it to see more info.</i>
            </b-card-body>
        </b-card>
    </div>
</template>

<script>
import { getAppRoot } from "onload/loadConfig";
import infiniteScroll from "vue-infinite-scroll";
import { openGlobalUploadModal } from "components/Upload";
import axios from "axios";

export default {
    directives: { infiniteScroll },
    props: {
        tools: {
            type: Array,
            default: null,
        },
        listView: {
            type: Boolean,
            default: false,
        },
    },
    data() {
        return {
            bufferLen: 4,
            busy: false,
            helpContents: {},
        };
    },
    computed: {
        buffer() {
            return this.listView ? this.tools : this.tools.slice(0, this.bufferLen);
        },
    },
    watch: {
        bufferLen() {
            this.buffer.forEach(async (tool, index) => {
                await this.fetchHelp(tool.id, index);
            });
        },
    },
    created() {
        const initData = { summary: "", help_text: "", toggle_help: false, is_fetched: false };
        const defaultHelpCont = {};
        this.tools.forEach((tool, index) => {
            defaultHelpCont[index] = { ...initData };
        });
        this.helpContents = { ...defaultHelpCont };
        this.buffer.forEach(async (tool, index) => {
            await this.fetchHelp(tool.id, index);
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
        loadMore() {
            if (this.buffer.length < this.tools.length) {
                this.busy = true;
                setTimeout(() => {
                    this.bufferLen += 4;
                    this.busy = false;
                }, 100);
            }
        },
        toggleHelp(key) {
            this.helpContents[key]["toggle_help"] = !this.helpContents[key]["toggle_help"];
        },
        async fetchHelp(id, key) {
            if (!this.helpContents[key]["is_fetched"]) {
                this.helpContents[key]["is_fetched"] = true; // tags the tool's help as being fetched
                this.busy = true;
                let helpText = "";
                let summary = null;
                await axios
                    .get(`${getAppRoot()}api/tools/${id}/build`)
                    .then((response) => {
                        helpText = response.data.help;
                    })
                    .catch((error) => {
                        console.error(error);
                    });
                this.busy = false;
                if (helpText && helpText != "\n") {
                    summary = this.parseHelp(helpText);
                } else {
                    helpText = ""; // for cases where helpText == '\n'
                }
                if (!summary) {
                    this.helpContents[key]["toggle_help"] = true;
                }
                this.helpContents[key]["summary"] = summary;
                this.helpContents[key]["help_text"] = helpText;
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
            if (!summary) {
                const helpText = helpDoc.documentElement.textContent;
                if (helpText) {
                    return helpText.substring(0, helpText.indexOf("\n\n"));
                }
            }
            return summary;
        },
    },
};
</script>
