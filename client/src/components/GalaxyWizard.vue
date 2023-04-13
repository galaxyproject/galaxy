<script setup lang="ts">
import axios from "axios";
import { ref } from "vue";
import Heading from "./Common/Heading.vue";

const props = defineProps({
    view: {
        type: String,
        default: "wizard",
    },
    query: {
        type: String,
        default: "",
    },
    context: {
        type: String,
        default: "",
    },
});

const query = ref(props.query);
const queryResponse = ref("");

const busy = ref(false);

if (props.context == "tool_error") {
    submitQuery();
}

// on submit, query the server and put response in display box
function submitQuery() {
    busy.value = true;
    queryResponse.value = "";
    const context = props.context || "username";
    axios
        .post("/api/chat", {
            query: query.value,
            context: context,
        })
        .then(function (response) {
            console.log(response);
            queryResponse.value = response.data;
        })
        .catch(function (error) {
            console.error(error);
        })
        .finally(() => {
            busy.value = false;
        });
}
</script>
<template>
    <div>
        <!-- input text, full width top of page -->
        <Heading v-if="props.view == 'wizard'" inline h2>Ask the wizard</Heading>
        <div class="mt-2">
            <b-input
                id="wizardinput"
                v-model="query"
                style="width: 100%"
                placeholder="What's the difference in fasta and fastq files?"
                :disabled="props.query !== ''"
                @keyup.enter="submitQuery" />
        </div>
        <!-- spinner when busy -->
        <div class="mt-4">
            <div v-if="busy">
                <b-skeleton animation="wave" width="85%"></b-skeleton>
                <b-skeleton animation="wave" width="55%"></b-skeleton>
                <b-skeleton animation="wave" width="70%"></b-skeleton>
            </div>
            <div v-else class="chatResponse">{{ queryResponse }}</div>
        </div>
    </div>
</template>
<style lang="scss" scoped>
.chatResponse {
    white-space: pre-wrap;
}
</style>
