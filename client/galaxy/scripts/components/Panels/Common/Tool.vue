<template>
    <div class="toolTitle">
        <a v-if="tool.disabled" class="name text-muted">
            <span v-if="!hideName">{{ tool.name }}</span>
            <span class="description">{{ tool.description }}</span>
        </a>
        <div v-else>
            <b-button
                v-if="!inFavorites && isUser"
                title="Add to Favorites"
                class="favorite-button ml-1 py-1"
                variant="link"
                v-on:click="onFavorite(tool.id)"
            >
                <i class="far fa-star"></i>
            </b-button>
            <b-button
                v-if="inFavorites && isUser"
                title="Remove from Favorites"
                variant="link"
                class="favorite-button ml-1 py-1"
                v-on:click="onUnfavorite(tool.id)"
            >
                <i class="fa fa-star"></i>
            </b-button>

            <b-button
                title=detailsText
                variant="link"
                class="info-button ml-1 py-1"
                v-on:click="toggleDetails"
            >
                <i class="fas fa-ellipsis-h"></i>
            </b-button>

            <a :class="targetClass" @click="onClick" :href="tool.link" :target="tool.target">
                <span class="labels">
                    <span
                        v-for="(label, index) in tool.labels"
                        :class="['badge', 'badge-primary', `badge-${label}`]"
                        :key="index"
                    >{{ label }}</span>
                </span>

                <span v-if="!hideName" class="name font-weight-bold">{{ tool.name }}</span>
                <span class="description">{{ tool.description }}</span>
                
                <span
                    v-b-tooltip.hover
                    :class="['operation', 'float-right', operationIcon]"
                    :title="operationTitle"
                    @click.stop.prevent="onOperation"
                />

                <div v-if="showDetails">
                    <span v-if="inputTypes">Accepted input types: {{ inputTypes }}</span>
                    <div
                        v-if="isRecEnabled && hasRelatedTools"
                        class="relatedTools"
                    >Related Tools: {{ relatedTools /*onRecommend(tool.id)*/ }}</div>
                </div>
            </a>
        </div>
    </div>
    <!--</div>-->
</template>

<script>
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import ariaAlert from "utils/ariaAlert";
import { getGalaxyInstance } from "app";
import { getToolPredictions } from "components/Workflow/Editor/modules/services";
import axios from "axios";

Vue.use(BootstrapVue);

export default {
    name: "Tool",
    props: {
        tool: {
            type: Object,
            required: true,
        },
        operationTitle: {
            type: String,
        },
        operationIcon: {
            type: String,
        },
        hideName: {
            type: Boolean,
        },
        toolKey: {
            type: String,
        },
    },
    data() {
        return {
            hasRelatedTools: false,
            relatedTools: [],
            inputTypes: "",
            inFavorites: false,
            showDetails: false,
            detailsText: "",
        };
    },
    computed: {
        targetClass() {
            if (this.toolKey) {
                return `tool-menu-item-${this.tool[this.toolKey]}`;
            } else {
                return null;
            }
        },
        isRecEnabled() {
            return getGalaxyInstance().config.enable_tool_recommendations;
        },
    },
    methods: {
        onClick(evt) {
            ariaAlert(`${this.tool.name} selected from panel`);
            this.$emit("onClick", this.tool, evt);
        },
        onOperation(evt) {
            ariaAlert(`${this.tool.name} operation selected from panel`);
            this.$emit("onOperation", this.tool, evt);
        },
        isFavorite() {
            return this.inFavorites = (getGalaxyInstance().user.getFavorites().tools.indexOf(this.tool.id) >= 0);
        },
        onRecommend(toolId) {
            const requestData = {
                tool_sequence: toolId,
            };
            console.log("PREDICTED TOOLS BEFORE: ", this.relatedTools);
            getToolPredictions(requestData)
                .then((responsePred) => {
                    const predictedData = responsePred.predicted_data.children;
                    if (predictedData.length > 0) {
                        this.hasRelatedTools = true;
                        predictedData.forEach((tool) => {
                            this.relatedTools.push(tool.name);
                        });
                    }
                    //return predictedData;
                })
                .catch((e) => {
                    console.error(e);
                });
            console.log("PREDICTED TOOLS AFTER: ", this.relatedTools);
        },
        getToolInputs(toolId) { //move to utilities
            const Galaxy = getGalaxyInstance();
            axios
                .get(`${Galaxy.root}api/tools/${toolId}/?io_details=true`)
                .then((response) => {
                    const firstInput = response.data.inputs[0].extensions;
                    this.inputTypes = firstInput ? firstInput.toString() : "";
                });
        },
        onFavorite(toolId) {
            //Add tool to user's favorites
            const Galaxy = getGalaxyInstance();
            axios.put(`${Galaxy.root}api/users/${Galaxy.user.id}/favorites/tools`, { object_id: toolId }).then((response) => {
                this.inFavorites = !this.inFavorites;
                Galaxy.user.updateFavorites("tools", response.data);
                ariaAlert("added to favorites");
            });
        },
        onUnfavorite(toolId) {
            //Remove tool from user's favorites
            const Galaxy = getGalaxyInstance();
            axios
                .delete(`${Galaxy.root}api/users/${Galaxy.user.id}/favorites/tools/${encodeURIComponent(toolId)}`)
                .then((response) => {
                    this.inFavorites = !this.inFavorites;
                    Galaxy.user.updateFavorites("tools", response.data);
                    ariaAlert("removed from favorites");
                });
        },
        toggleDetails() {
            this.showDetails = !this.showDetails;
            this.setDetailsText();
        },
        setDetailsText() {
            this.deatilsText = this.showDetails ? "Show less information" : "Show more information";
        },
        isUser() {
            const Galaxy = getGalaxyInstance();
            return !!(Galaxy.user && Galaxy.user.id);
        },
    },
    created() {
        this.inFavorites = this.isFavorite();
        this.onRecommend(this.tool.id);
        this.getToolInputs(this.tool.id);
    },
};
</script>

<style>
/*div.toolTitle, div.favorite-button, a, button {
    display: inline;
}*/
</style>
