<template>
    <div v-infinite-scroll="loadMore" infinite-scroll-disabled="busy">
        <h2 class="mb-3">
            <span id="tools-view">Tools View</span>
        </h2>
        <div v-if="!loading">
            <b-container fluid class="mb-4">
                <b-row>
                    <b-col md="6">
                        <b-form-group description="Search for strings or regular expressions">
                            <b-input-group>
                                <b-form-input
                                    v-model="filter"
                                    placeholder="Type to Search"
                                    @keyup.esc.native="filter = ''"
                                />
                                <b-input-group-append>
                                    <b-btn :disabled="!filter" @click="filter = ''">Clear (esc)</b-btn>
                                </b-input-group-append>
                            </b-input-group>
                        </b-form-group>
                    </b-col>
                </b-row>
            </b-container>
            <b-card-group v-for="(deck, dindex) in bufferView" :key="dindex" deck class="mb-4">
                <b-card v-for="(info, index) in deck" :key="index" itemscope itemtype="http://schema.org/SoftwareApplication">
                    <meta itemprop="operatingSystem" content="Any">
                    <meta itemprop="applicationCategory" content="Web application">
                    <div slot="header">
                        <b-link :href="info['url']" target="_blank" itemprop="url">
                            <h4 itemprop="name">{{ info["name"] }}</h4>
                        </b-link>
                        <b-badge>{{ info["section"] }}</b-badge>
                    </div>
                    <p class="card-text" v-html="helpSummary(info['help']) || info['description']" itemprop="description"/>
                    <p class="card-text">
                        <b-btn v-b-modal="'modal-' + dindex + '-' + index">Info</b-btn>
                        <b-modal :id="'modal-' + dindex + '-' + index" centered :title="info['name']">
                            <b itemprop="softwareVersion">{{ info["version"] + " / " + info["id"] }}</b>
                            <p>{{ info["description"] }}</p>
                            <p v-html="info['help']"></p>
                        </b-modal>
                    </p>
                    <Citations simple source="tools" :id="info['id']" itemprop="citation"/>
                </b-card>
            </b-card-group>
        </div>
    </div>
</template>

<script>
import { getAppRoot } from "onload/loadConfig";
import infiniteScroll from "vue-infinite-scroll";
import axios from "axios";
import Citations from "components/Citations.vue";

export default {
    components: {
        Citations
    },
    directives: { infiniteScroll },
    data() {
        return {
            tools: [],
            buffer: [],
            filter: "",
            busy: false,
            loading: true
        };
    },
    computed: {
        bufferView() {
            let a = [];
            let b = this.bufferFiltered.slice(0);
            while (b.length) a.push(b.splice(0, 3));
            return a;
        },
        bufferFiltered() {
            let f = [];
            let filter = this.filter;
            if (!this.loading) {
                f = this.buffer.filter(x => {
                    let re = new RegExp(filter, "i");
                    return x["name"].match(re) || x["description"].match(re);
                });
            }
            return f;
        }
    },
    methods: {
        toolsExtracted(tools) {
            function extractSections(acc, section) {
                function extractTools(_acc, tool) {
                    return tool["name"]
                        ? [
                              ..._acc,
                              {
                                  id: tool["id"],
                                  name: tool["name"],
                                  section: section["name"],
                                  description: tool["description"],
                                  url: getAppRoot() + String(tool["link"]).substring(1),
                                  version: tool["version"],
                                  help: tool["help"]
                              }
                          ]
                        : _acc;
                }
                return acc.concat(section["elems"].reduce(extractTools, []));
            }
            return tools
                .reduce(extractSections, [])
                .map(a => [Math.random(), a])
                .sort((a, b) => a[0] - b[0])
                .map(a => a[1]);
        },
        loadMore() {
            this.busy = true;

            setTimeout(() => {
                const start = this.buffer.length;
                const end = start + 20;
                this.buffer = this.buffer.concat(this.tools.slice(start, end));
                this.busy = false;
            }, 1000);
        },
        helpSummary(help) {
            const parser = new DOMParser();
            const helpDoc = parser.parseFromString(help, "text/html");
            const xpath = "//strong[text()='What it does']/../following-sibling::*";
            const match = helpDoc.evaluate(xpath, helpDoc, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null)
                .singleNodeValue;
            if (match) {
                return match.innerHTML;
            } else {
                const helpText = helpDoc.documentElement.textContent;
                if (helpText) {
                    return helpText.substring(0, helpText.indexOf("\n\n"));
                } else {
                    return null;
                }
            }
        }
    },
    created() {
        axios
            .get(`${getAppRoot()}api/tools?tool_help=True`)
            .then(response => {
                this.tools = this.toolsExtracted(response.data);
                this.buffer = this.tools.slice(0, 20);
                this.loading = false;
            })
            .catch(error => {
                console.error(error);
            });
    }
};
</script>
