<script setup>
import axios from "axios";
import { ref, computed } from "vue";
import Heading from "./Common/Heading.vue";

const query = ref("");
const queryResponse = ref("");

const queryDisabled = computed(() => !(query.value.length > 0));

// on submit, query the server and put response in display box
function submitQuery() {
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
        <div class="mt-4">
            {{ queryResponse }}
        </div>
    </div>
</template>
<style lang="scss" scoped></style>
