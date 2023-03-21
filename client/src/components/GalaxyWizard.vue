<script setup>
import axios from "axios";
import { ref } from "vue";
import Heading from "./Common/Heading.vue";

const query = ref("");
const queryResponse = ref("");

const busy = ref(false);

// on submit, query the server and put response in display box
function submitQuery() {
    busy.value = true;
    queryResponse.value = "";
    axios
        .post("/api/chat", {
            query: query.value,
        })
        .then(function (response) {
            console.log(response);
            queryResponse.value = response.data;
        })
        .catch(function (error) {
            console.log(error);
        })
        .finally(() => {
            busy.value = false;
        });
}
</script>
<template>
    <div>
        <!-- input text, full width top of page -->
        <Heading inline h2>Ask the wizard</Heading>
        <div class="mt-2">
            <b-input
                id="wizardinput"
                v-model="query"
                style="width: 100%"
                placeholder="What's the difference in fasta and fastq?"
                @keyup.enter="submitQuery" />
        </div>
        <!-- input button  -->
        <!--
        <div class="mt-2">
            <button :disabled="queryDisabled" @click.prevent="submitQuery">Query</button>
        </div>
        -->
        <!-- spinner when busy -->
        <div class="mt-4">
            <div v-if="busy">
                <b-skeleton animation="wave" width="85%"></b-skeleton>
                <b-skeleton animation="wave" width="55%"></b-skeleton>
                <b-skeleton animation="wave" width="70%"></b-skeleton>
            </div>
            {{ queryResponse }}
        </div>
    </div>
</template>
<style lang="scss" scoped></style>
