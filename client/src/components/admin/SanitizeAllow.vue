<template>
    <div>
        <message :message="message" :status="status"></message>
        <component
            :is="currentView"
            v-if="status !== 'error'"
            v-bind="currentProps"
        >
        </component>
    </div>
</template>

<script>
import { getAppRoot } from "onload/loadConfig";
import axios from "axios";
import Message from "../Message.vue";
import SanitizeAllowGrid from "./SanitizeAllowGrid.vue";

export default {
    data() {
        return {
            currentView: "sanitize-allow-grid",
            isLoaded: false,
            localAllowed: [],
            localBlocked: [],
            toolshedAllowed: [],
            toolshedBlocked: [],
            message: "",
            status: "",
        };
    },

    components: {
        message: Message,
        "sanitize-allow-grid": SanitizeAllowGrid,
    },

    computed: {
        currentProps() {
            let props;

            if (this.currentView === "sanitize-allow-grid") {
                props = {
                    isLoaded: this.isLoaded,
                    localAllowed: this.localAllowed,
                    localBlocked: this.localBlocked,
                    toolshedAllowed: this.toolshedAllowed,
                    toolshedBlocked: this.toolshedBlocked,
                };
            }

            return props;
        },
    },

    created() {
        axios
            .get(`${getAppRoot()}api/sanitize_allow`)
            .then((response) => {
                this.isLoaded = true;
                this.localAllowed = response.data.data.allowed_local;
                this.localBlocked = response.data.data.blocked_local;
                this.toolshedAllowed = response.data.data.allowed_toolshed;
                this.toolshedBlocked = response.data.data.blocked_toolshed;
                this.message = response.data.message;
                this.status = response.data.status;
            })
            .catch((error) => {
                console.error(error);
            });
    },
};
</script>
