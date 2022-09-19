<template>
    <div v-infinite-scroll="loadMore" infinite-scroll-disabled="busy">
        <h2 class="mb-3" style="text-align: center">
            <span id="tools-view">Consolidated view of {{ tools.length }} available tools.</span>
        </h2>
        <div v-if="!loading">
            <b-container fluid class="mb-4">
                <b-row class="justify-content-center">
                    <b-col md="6">
                        <b-form-group description="Search for strings or regular expressions">
                            <b-input-group>
                                <b-form-input
                                    v-model="filterText"
                                    placeholder="Type to Search"
                                    @keyup.native="filter('filterByText')"
                                    @keyup.esc.native="filterText = ''" />
                                <b-input-group-append>
                                    <b-btn :disabled="!filter" @click="filter = ''">Clear (esc)</b-btn>
                                </b-input-group-append>
                            </b-input-group>
                        </b-form-group>
                    </b-col>
                </b-row>
            </b-container>
            <isotope
                ref="iso"
                :options="isoOptions"
                :list="buffer"
                style="margin: 0 auto"
                @filter="filterOption = arguments[2]">
                <b-card v-for="(info, index) in buffer" :key="index" ref="cards" class="m-2" style="width: 23rem">
                    <template v-slot:header>
                        <div>
                            <b-link :href="info.url" target="_blank">
                                <h4 class="tools-view-name">{{ info.name }}</h4>
                            </b-link>
                            <b-badge class="tools-view-section">{{ info.section }}</b-badge>
                        </div>
                    </template>
                    <p class="card-text" v-html="helpSummary(info.help) || info.description" />
                    <p class="card-text">
                        <b-btn v-b-modal="'modal-' + '-' + index" :index="index">Info</b-btn>
                        <b-modal :id="'modal-' + '-' + index" centered ok-only :static="true" :title="info.name">
                            <b>{{ info.version + " / " + info.id }}</b>
                            <p>{{ info.description }}</p>
                            <p v-html="info.help"></p>
                        </b-modal>
                    </p>
                    <Citations
                        :id="info.id"
                        simple
                        source="tools"
                        @rendered="layout"
                        @show="show(index)"
                        @shown="shown(index)"
                        @hidden="hidden(index)" />
                </b-card>
            </isotope>
        </div>
    </div>
</template>

<script>
import { getAppRoot } from "onload/loadConfig";
import infiniteScroll from "vue-infinite-scroll";
import isotope from "vueisotope";
import axios from "axios";
import Citations from "components/Citation/Citations.vue";
import { setTimeout } from "timers";

export default {
    components: {
        Citations,
        isotope,
    },
    directives: { infiniteScroll },
    props: {
        transitionDuration: {
            type: Number,
            default: 200,
        },
    },
    data() {
        return {
            tools: [],
            buffer: [],
            filterOption: null,
            filterText: "",
            busy: false,
            loading: true,
        };
    },
    computed: {
        isoOptions() {
            return {
                transitionDuration: this.transitionDuration,
                masonry: {
                    fitWidth: true,
                },
                getFilterData: {
                    filterByText: (el) => {
                        const re = new RegExp(this.filterText, "i");
                        return el.name.match(re) || el.description.match(re) || el.help.match(re);
                    },
                },
            };
        },
    },
    created() {
        axios
            .get(`${getAppRoot()}api/tools?tool_help=True`)
            .then((response) => {
                this.initialize(response.data);
            })
            .catch((error) => {
                console.error(error);
            });
    },
    methods: {
        show(index) {
            this.$refs.cards[index].style.zIndex = "1";
        },
        shown(index) {
            this.layout();
            setTimeout(() => {
                this.$refs.cards[index].style.zIndex = "auto";
            }, 200);
        },
        hidden(index) {
            this.layout();
        },
        layout() {
            this.$refs.iso.layout();
        },
        filter(key) {
            this.$refs.iso.filter(key);
        },
        toolsExtracted(tools) {
            function extractSections(acc, section) {
                function extractTools(_acc, tool) {
                    return tool.name
                        ? [
                              ..._acc,
                              {
                                  id: tool.id,
                                  name: tool.name,
                                  section: section.name,
                                  description: tool.description,
                                  url: getAppRoot() + String(tool.link).substring(1),
                                  version: tool.version,
                                  help: tool.help,
                              },
                          ]
                        : _acc;
                }
                if ("elems" in section) {
                    return acc.concat(section.elems.reduce(extractTools, []));
                }
                return acc;
            }
            return tools
                .reduce(extractSections, [])
                .map((a) => [Math.random(), a])
                .sort((a, b) => a[0] - b[0])
                .map((a) => a[1]);
        },
        loadMore() {
            if (this.buffer.length < this.tools.length) {
                this.busy = true;

                setTimeout(() => {
                    const start = this.buffer.length;
                    const end = start + 10;
                    const newItems = this.tools.slice(start, end);
                    this.buffer = this.buffer.concat(newItems);

                    this.busy = false;
                }, 100);
            }
        },
        helpSummary(help) {
            const parser = new DOMParser();
            const helpDoc = parser.parseFromString(help, "text/html");
            const xpath = "//strong[text()='What it does']/../following-sibling::*";
            const match = helpDoc.evaluate(
                xpath,
                helpDoc,
                null,
                XPathResult.FIRST_ORDERED_NODE_TYPE,
                null
            ).singleNodeValue;
            if (match) {
                return match.innerHTML;
            }
            const helpText = helpDoc.documentElement.textContent;
            if (helpText) {
                return helpText.substring(0, helpText.indexOf("\n\n"));
            }
            return null;
        },
        getToolsNumber() {
            return this.tools.length;
        },
        initialize(tools) {
            this.tools = this.toolsExtracted(tools);
            this.buffer = this.tools.slice(0, 20);
            this.loading = false;
        },
    },
};
</script>
