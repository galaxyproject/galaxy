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
            allowList: [],
            blockList: [],
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
                    allow: this.allowList,
                    sanitize: this.blockList,
                };
            }

            return props;
        },
    },

    created() {
        axios
            .get(`${getAppRoot()}api/sanitize_allowlist`)
            .then((response) => {
                this.isLoaded = true;
                this.allowList = response.data.data.allow;
                this.blockList = response.data.data.sanitize;
                this.message = response.data.message;
                this.status = response.data.status;
                console.log(this.allowList);
            })
            .catch((error) => {
                console.error(error);
            });
    },
};
</script>
