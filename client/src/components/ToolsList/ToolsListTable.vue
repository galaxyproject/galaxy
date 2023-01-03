<template>
    <div
        v-infinite-scroll="loadTools"
        class="tools-list-table"
        infinite-scroll-distance="200"
        infinite-scroll-disabled="busy">
        <ToolsListItem
            v-for="item of buffer"
            :id="item.id"
            :key="item.id"
            :name="item.name"
            :section="item.panel_section_name"
            :description="item.description"
            :summary="item.summary"
            :help="item.help"
            :local="item.target === 'galaxy_main'"
            :link="item.link"
            :workflow-compatible="item.is_workflow_compatible"
            :version="item.version"
            @open="() => onOpen(item)" />
        <div>
            <div v-if="allLoaded" class="list-end my-2">- End of search results -</div>
            <b-overlay :show="busy" opacity="0.5" />
        </div>
    </div>
</template>

<script>
import Vue from "vue";
import infiniteScroll from "vue-infinite-scroll";
import { useGlobalUploadModal } from "composables/globalUploadModal";
import { fetchData } from "./services";
import ToolsListItem from "./ToolsListItem";

const defaultBufferLen = 4;
const loadTimeout = 100;

export default {
    components: { ToolsListItem },
    directives: { infiniteScroll },
    props: {
        tools: {
            type: Array,
            default: null,
        },
    },
    setup() {
        const { openGlobalUploadModal } = useGlobalUploadModal();
        return { openGlobalUploadModal };
    },
    data() {
        return {
            allLoaded: false,
            bufferLen: 0,
            busy: false,
        };
    },
    computed: {
        buffer() {
            return this.tools.slice(0, this.bufferLen);
        },
    },
    created() {
        this.loadTools();
    },
    methods: {
        onOpen(tool) {
            if (tool.id === "upload1") {
                this.openGlobalUploadModal();
            } else if (tool.form_style === "regular") {
                // encode spaces in tool.id
                const toolId = tool.id;
                const toolVersion = tool.version;
                this.$router.push({ path: `/?tool_id=${encodeURIComponent(toolId)}&version=${toolVersion}` });
            }
        },
        loadTools() {
            if (this.tools && !this.busy && this.bufferLen < this.tools.length) {
                this.busy = true;
                setTimeout(() => {
                    this.bufferLen += defaultBufferLen;
                    this.tools.slice(this.bufferLen - defaultBufferLen, this.bufferLen).forEach(async (tool) => {
                        await this.fetchHelp(tool);
                    });
                    this.busy = false;
                }, loadTimeout);
            } else if (this.bufferLen >= this.tools.length) {
                this.allLoaded = true;
            }
        },
        async fetchHelp(tool) {
            await fetchData(`api/tools/${tool.id}/build`).then((response) => {
                const help = response.help;
                Vue.set(tool, "_showDetails", false); // maybe not needed
                if (help && help != "\n") {
                    Vue.set(tool, "help", help);
                    Vue.set(tool, "summary", this.parseHelp(help));
                } else {
                    Vue.set(tool, "help", ""); // for cases where helpText == '\n'
                }
            });
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

<style lang="scss" scoped>
@import "theme/blue.scss";

.tools-list-table {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;

    .list-end {
        width: 100%;
        text-align: center;
        color: $text-light;
    }
}
</style>
