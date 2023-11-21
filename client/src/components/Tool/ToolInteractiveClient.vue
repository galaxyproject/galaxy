<template>
    <div>
        <ToolCard
            v-if="showTool"
            :id="toolConfig.id"
            :version="toolConfig.version"
            :title="toolConfig.name"
            :description="toolConfig.description"
            :options="toolConfig"
            :disabled="disableTool"
            :allow-object-store-selection="config.object_store_allows_id_selection"
            :preferred-object-store-id="preferredObjectStoreId"
            @onChangeVersion="onChangeVersion"
            @onSetError="onSetError"
            @updatePreferredObjectStoreId="onUpdatePreferredObjectStoreId">
            <template v-slot:extra-tool-options-items>
                <b-dropdown-item :disabled="!serviceToolExists" @click="openServiceTool">
                    <FontAwesomeIcon icon="fa-wrench" /><span v-localize>Open Service tool</span>
                </b-dropdown-item>
            </template>

            <template v-slot:body>
                <FontAwesomeIcon v-if="!triedToFetchServiceToolInfo" icon="spinner" class="ml-3 mr-2 mt-4" spin />
                <slot name="tool-messages" />
                <CenterFrame
                    id="interactive_client_frame"
                    :height="iframeLoaded ? iframeHeight : '0px'"
                    :src="serviceStarting ? '' : iframeSrc"
                    @load="onLoadIframe()" />
                <FontAwesomeIcon v-if="iframeLoading || loading" icon="spinner" class="ml-3 mr-2" spin />
            </template>

            <template v-slot:header-buttons>
                <ButtonSpinner
                    v-if="!serviceToolEntryPoint || serviceStarting"
                    id="start-service-button"
                    :title="serviceStarting ? 'Starting Service...' : 'Start Service'"
                    class="btn-sm"
                    :disabled="!serviceToolExists"
                    :wait="serviceStarting"
                    tooltip="Start the related interactive tool service"
                    @onClick="startService()" />

                <ButtonSpinner
                    v-if="serviceToolEntryPoint && !serviceStarting"
                    id="stop-service-button"
                    :title="serviceStopping ? 'Stopping Service...' : 'Stop Service'"
                    class="btn-sm"
                    icon="stop"
                    :disabled="!serviceToolExists"
                    :wait="serviceStopping"
                    tooltip="Stop the related interactive tool service"
                    @onClick="stopService()" />
            </template>
            <template v-slot:buttons> </template>
        </ToolCard>
    </div>
</template>

<script>
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import axios from "axios";
import { Services } from "components/InteractiveTools/services";
import { useConfig } from "composables/config";
import { getAppRoot } from "onload/loadConfig";
import { mapActions, mapState } from "pinia";
import { useEntryPointStore } from "stores/entryPointStore";
import { useJobStore } from "stores/jobStore";
import { refreshContentsWrapper } from "utils/data";
import { withPrefix } from "utils/redirect";

import { submitJob } from "./services";

import ToolCard from "./ToolCard.vue";
import ButtonSpinner from "components/Common/ButtonSpinner.vue";
import CenterFrame from "entry/analysis/modules/CenterFrame.vue";

export default {
    components: {
        CenterFrame,
        ButtonSpinner,
        FontAwesomeIcon,
        ToolCard,
    },
    props: {
        toolConfig: {
            type: Object,
            required: true,
        },
        showTool: {
            type: Boolean,
            required: true,
        },
        disableTool: {
            type: Boolean,
            default: false,
        },
        loading: {
            type: Boolean,
            default: false,
        },
    },
    setup() {
        const { config, isConfigLoaded } = useConfig(true);
        return { config, isConfigLoaded };
    },
    data() {
        return {
            preferredObjectStoreId: null, // Placeholder - support added later, if needed
            clientToolConfigInspected: false,
            clientToolConfigValid: false,
            serviceToolEntryPoint: null,
            allServiceToolEntryPoints: [],
            triedToFetchServiceToolInfo: false,
            serviceToolInfo: null,
            serviceStarting: false,
            serviceStopping: false,
            iframeLoaded: false,
            iframeSrc: null,
            refreshIframeHeightFlip: false,
        };
    },
    computed: {
        ...mapState(useEntryPointStore, { activeEntryPoints: "entryPoints" }),

        serviceToolId() {
            console.log(this.toolConfig.interactive_service_tool_id);
            return this.toolConfig.interactive_service_tool_id;
        },
        serviceToolVersion() {
            console.log(this.toolConfig.interactive_service_tool_version);
            return this.toolConfig.interactive_service_tool_version;
        },
        serviceToolEntryPointLabel() {
            console.log(this.toolConfig.interactive_service_entrypoint_label);
            return this.toolConfig.interactive_service_entrypoint_label;
        },
        serviceToolExists() {
            console.log(`serviceToolExists: ${this.triedToFetchServiceToolInfo && this.serviceToolInfo !== null}`);
            return this.triedToFetchServiceToolInfo && this.serviceToolInfo !== null;
        },
        entryPointPollingTimeout() {
            return this.serviceStarting && !this.iframeLoading && !this.serviceStopping ? 1000 : 2500;
        },
        httpPost() {
            return true;
        },
        serviceToolEntryPointTarget() {
            return this.serviceToolEntryPoint?.target;
        },
        clientToolParams() {
            const params = { ...this.toolConfig.state_inputs }; // copy
            if (this.httpPost && this.serviceToolEntryPointTarget) {
                const target_url = new URL(this.serviceToolEntryPointTarget, window.location.origin);
                params.entrypoint_target_url = target_url.href;
            }
            params.interactive_client_tool_id = this.toolConfig.id;
            params.interactive_client_tool_version = this.toolConfig.version;
            return params;
        },
        iframeLoading() {
            return this.serviceToolEntryPointTarget && !this.iframeLoaded;
        },
        iframeHeight() {
            this.refreshIframeHeightFlip;

            if (this.iframeLoaded) {
                const iframeWindow = this.getIframeWindow();
                if (iframeWindow) {
                    const html = iframeWindow.document.documentElement;

                    // Idea from https://stackoverflow.com/a/64110252
                    if (html) {
                        html.style.overflowX = "auto";
                        html.style.overflowY = "hidden";
                        const htmlStyle = iframeWindow.getComputedStyle(html);
                        const htmlHeight = parseInt(htmlStyle.getPropertyValue("height"));

                        return `${htmlHeight}px`;
                    }
                }
            }
            return "0px";
        },
    },
    watch: {
        toolConfig() {
            console.log("load");
            this.load();
        },
        async clientToolConfigInspected() {
            console.log("clientToolConfigInspected");
            if (!this.clientToolConfigInspected) {
                this.inspectClientToolConfig();
            } else {
                const prevActiveEntryPoints = this.activeEntryPoints;
                await this.fetchEntryPointsAndRegisterPollingTimeout();

                if (this.activeEntryPoints === prevActiveEntryPoints) {
                    // activeEntryPoints watcher will not trigger
                    await this.findServiceToolEntryPoint();
                }
            }
        },
        async entryPointPollingTimeout() {
            console.log("entryPointPollingTimeout");
            await this.fetchEntryPointsAndRegisterPollingTimeout();
        },
        async activeEntryPoints() {
            console.log(`activeEntryPoints at ${new Date().toLocaleString()}`);
            await this.findServiceToolEntryPoint();
        },
        async serviceToolEntryPoint() {
            console.log("serviceToolEntryPoint");
            await this.setServiceToolErrorsIfNeeded();
        },
        async serviceToolEntryPointTarget() {
            console.log("serviceToolEntryPointTarget");
            if (this.serviceToolEntryPointTarget) {
                if (this.serviceStarting) {
                    this.iframeSrc = await this.getIframeSrc({ waitForPageLoad: true });
                    this.serviceStarting = false;
                } else {
                    this.iframeSrc = await this.getIframeSrc({ waitForPageLoad: false });
                }
            } else {
                this.iframeSrc = null;
            }
        },
    },
    async created() {
        console.log("created");
        this.root = getAppRoot();
        this.interactiveToolsServices = new Services({ root: this.root });
        this.load();
    },
    async beforeDestroy() {
        console.log("beforeDestroy");
        await this.ensurePollingEntryPoints();
        this.removeIframeEventListeners();
    },
    methods: {
        ...mapActions(useEntryPointStore, ["ensurePollingEntryPoints"]),

        load() {
            this.resetData();
            this.$nextTick(() => {
                this.inspectClientToolConfig();
            });
        },
        resetData() {
            this.clientToolConfigInspected = false;
            this.clientToolConfigValid = false;
            this.serviceToolEntryPoint = null;
            this.allServiceToolEntryPoints = [];
            this.triedToFetchServiceToolInfo = false;
            this.serviceToolInfo = null;
            this.iframeLoaded = false;
            this.serviceStarting = false;
        },
        async onChangeVersion(newVersion) {
            this.$emit("onChangeVersion", newVersion);
        },
        onSetError(errorObj) {
            this.$emit("onSetError", errorObj);
        },
        onUpdatePreferredObjectStoreId(preferredObjectStoreId) {
            this.preferredObjectStoreId = preferredObjectStoreId;
        },
        inspectClientToolConfig() {
            console.log("inspectClientToolConfig");
            const validate_properties = [
                { value: this.serviceToolId, attr: "interactive_service_tool_id", desc: "Tool id" },
                { value: this.serviceToolVersion, attr: "interactive_service_tool_version", desc: "Tool version" },
                {
                    value: this.serviceToolEntryPointLabel,
                    attr: "interactive_service_entrypoint_label",
                    desc: "Entry point label",
                },
            ];

            let valid = true;
            for (const prop of validate_properties) {
                if (!prop.value) {
                    this.onSetError({
                        message: `Error: ${prop.desc} for required interactive tool service has not been set for interactive
                                  client tool "${this.toolConfig.id}". Please set the "${prop.attr}" attribute of the
                                  "inputs" tab accordingly.`,
                    });

                    valid = false;
                    break;
                }
            }
            this.clientToolConfigValid = valid;
            this.clientToolConfigInspected = true;
        },
        async fetchEntryPointsAndRegisterPollingTimeout() {
            console.log("fetchEntryPointsAndRegisterPollingTimeout");
            await this.ensurePollingEntryPoints(this.entryPointPollingTimeout);
        },
        async findServiceToolEntryPoint() {
            if (this.clientToolConfigValid) {
                console.log("finding correct entry point");
                const jobStore = useJobStore();
                const allServiceToolEntryPoints = {};

                for (const entryPoint of this.activeEntryPoints) {
                    let creatingJob = jobStore.getJob(entryPoint.job_id);

                    if (!creatingJob) {
                        console.log(`fetching job: ${entryPoint.job_id}`);
                        await jobStore.fetchJob(entryPoint.job_id);
                        creatingJob = jobStore.getJob(entryPoint.job_id);
                    }

                    if (creatingJob.tool_id === this.serviceToolId) {
                        if (!(creatingJob.tool_version in allServiceToolEntryPoints)) {
                            allServiceToolEntryPoints[creatingJob.tool_version] = [];
                        }
                        allServiceToolEntryPoints[creatingJob.tool_version].push(entryPoint);
                    }
                }

                let version = this.serviceToolVersion;
                if (!(version in allServiceToolEntryPoints)) {
                    await this.fetchServiceToolInfo();
                    if (this.serviceToolExists) {
                        version = this.serviceToolInfo.version;
                    }
                }

                let serviceToolEntryPoint = null;
                if (version in allServiceToolEntryPoints) {
                    for (const entryPoint of allServiceToolEntryPoints[version]) {
                        if (entryPoint.label === this.serviceToolEntryPointLabel) {
                            this.onSetError(null);
                            serviceToolEntryPoint = entryPoint;
                            this.allServiceToolEntryPoints = allServiceToolEntryPoints[version];
                            break;
                        }
                    }
                }
                this.serviceToolEntryPoint = serviceToolEntryPoint;
                await this.setServiceToolErrorsIfNeeded();
                console.log("finished finding correct entry point");
            }
        },
        async setServiceToolErrorsIfNeeded() {
            await this.fetchServiceToolInfo();
            if (this.serviceToolExists) {
                const reqVersion = this.serviceToolVersion;
                const foundVersion = this.serviceToolInfo.version;
                const isWrongVersion = reqVersion !== foundVersion;
                const startOfMessage = `
                    Required interactive tool service "${this.serviceToolId}" with version "${reqVersion}"
                    ${isWrongVersion ? `is not installed, however version "${foundVersion}" of the tool` : ""}
                    is available`;

                if (!this.serviceToolEntryPoint) {
                    console.log("setNotRunningError");
                    this.onSetError({
                        message: `${startOfMessage} but not running. Click the "Start Service" button in the tool
                                  header to start the service with default input values. Alternatively, to edit the
                                  tool form before starting the service, select "Open Service tool" from the popup
                                  menu (downwards triangle).`,
                    });
                } else if (isWrongVersion) {
                    console.log(`setWrongVersionError ${foundVersion}`);
                    this.onSetError({
                        message: `${startOfMessage}. Connecting to version "${foundVersion}" of the service instead.
                                  This may cause errors or other unintended consequences. Please proceed at your own
                                  risk!`,
                    });
                }
            }
        },
        async fetchServiceToolInfo() {
            console.log(`fetchServiceToolInfo ${this.triedToFetchServiceToolInfo}`);
            if (!this.triedToFetchServiceToolInfo) {
                try {
                    console.time();
                    const response = await axios.get(
                        getAppRoot() + `api/tools/${this.serviceToolId}?tool_version=${this.serviceToolVersion}`
                    );
                    console.assert(response.data.version === this.serviceToolVersion);
                    this.serviceToolInfo = response.data;
                    console.timeEnd();
                } catch (error) {
                    this.onSetError({
                        message: `Loading interactive client tool "${this.toolConfig.id}" failed due to an error
                                  loading required interactive tool service "${this.serviceToolId}" with version
                                  "${this.serviceToolVersion}": ${error?.response?.data?.err_msg}`,
                    });
                }
            }
            this.triedToFetchServiceToolInfo = true;
        },
        async getIframeSrc({ waitForPageLoad }) {
            console.log(`getIframeSrc(waitForPageLoad=${waitForPageLoad}`);
            let ok = false;
            let iframeSrc = null;
            while (!ok) {
                try {
                    if (this.httpPost) {
                        const { data } = await axios.post(this.serviceToolEntryPointTarget, this.clientToolParams);
                        const blob = new Blob([data], { type: "text/html" });
                        iframeSrc = URL.createObjectURL(blob);
                    } else {
                        const getParams = new URLSearchParams(this.clientToolParams).toString();
                        iframeSrc = `${this.serviceToolEntryPointTarget}?${getParams}`;
                        if (waitForPageLoad) {
                            await axios.get(withPrefix(iframeSrc));
                        }
                    }
                    ok = true;
                } catch (error) {
                    console.log(error);
                    if (!waitForPageLoad) {
                        this.onSetError({
                            message: error.message,
                            title: "Error sending HTTP request to service tool.",
                        });
                    }
                    await new Promise((resolve) => setTimeout(resolve, 1000));
                    this.onSetError(null);
                }
            }
            return iframeSrc;
        },
        openServiceTool() {
            this.$router.push(`/root?tool_id=${this.serviceToolId}&tool_version=${this.serviceToolVersion}`);
        },
        async startService() {
            this.serviceStarting = true;

            const jobDef = {
                tool_id: this.serviceToolId,
                tool_version: this.serviceToolVersion,
            };

            try {
                const jobResponse = await submitJob(jobDef);
                refreshContentsWrapper();
                const nJobs = jobResponse && jobResponse.jobs ? jobResponse.jobs.length : 0;
                if (nJobs === 0) {
                    this.onSetError({
                        dialog: true,
                        message: "",
                        title: "Job submission rejected.",
                        content: jobResponse,
                    });
                    this.serviceStarting = false;
                }
            } catch (error) {
                this.onSetError({
                    dialog: true,
                    message: error,
                    title: "Job submission failed.",
                    content: jobDef,
                });
                this.serviceStarting = false;
            }
        },
        async stopService() {
            this.serviceStopping = true;
            for (const entryPoint of this.allServiceToolEntryPoints) {
                await this.interactiveToolsServices.stopInteractiveTool(entryPoint.id);
            }
            this.serviceToolEntryPoint = null;
            this.allServiceToolEntryPoints = [];

            this.serviceStopping = false;
        },
        getIframeElement() {
            return window.top.document.getElementById("interactive_client_frame");
        },
        getIframeWindow() {
            return this.getIframeElement()?.contentWindow;
        },
        onLoadIframe() {
            console.log("onLoadIframe");
            if (this.iframeSrc) {
                this.addIframeEventListeners();
                this.iframeLoaded = true;
            } else {
                this.iframeLoaded = false;
            }
            this.refreshIframeHeight();
        },
        addIframeEventListeners() {
            console.log("addIframeEventListeners");
            const iframeWindow = this.getIframeWindow();
            if (iframeWindow) {
                iframeWindow.addEventListener("resize", this.refreshIframeHeight);
                iframeWindow.addEventListener("mousedown", this.shortSleepAndRefreshIframeHeight);
                iframeWindow.addEventListener("mouseup", this.shortSleepAndRefreshIframeHeight);
                iframeWindow.addEventListener("keydown", this.shortSleepAndRefreshIframeHeight);
                iframeWindow.addEventListener("beforeunload", this.removeIframeEventListeners);
            }
        },
        removeIframeEventListeners() {
            console.log("removeIframeEventListeners");
            const iframeWindow = this.getIframeWindow();
            if (iframeWindow) {
                iframeWindow.removeEventListener("resize", this.refreshIframeHeight);
                iframeWindow.removeEventListener("mousedown", this.shortSleepAndRefreshIframeHeight);
                iframeWindow.removeEventListener("mouseup", this.shortSleepAndRefreshIframeHeight);
                iframeWindow.removeEventListener("keydown", this.shortSleepAndRefreshIframeHeight);
                iframeWindow.removeEventListener("beforeunload", this.removeIframeEventListeners);
            }
        },
        async refreshIframeHeight(event) {
            this.refreshIframeHeightFlip = !this.refreshIframeHeightFlip;
        },
        async shortSleepAndRefreshIframeHeight(event) {
            await new Promise((resolve) => setTimeout(resolve, 1));
            this.refreshIframeHeight();
        },
    },
};
</script>
