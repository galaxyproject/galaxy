<script setup>
import { ref } from "vue";
import { useGetDetailedDatatypes } from "composables/datatypes";
import { useFilterObjectArray } from "composables/filter";
import DelayedInput from "components/Common/DelayedInput";

const fields = ["extension"];

const filter = ref("");

const { datatypes } = useGetDetailedDatatypes();
const filteredArray = useFilterObjectArray(datatypes, filter, fields);
</script>

<template>
    <div>
        <h1>Datatypes</h1>
        <DelayedInput :delay="200" @change="(val) => (filter = val)" />
        <div v-for="datatype in filteredArray" :key="datatype.extension">
            <div>{{ datatype.extension }}</div>
        </div>
    </div>
</template>

<style scoped></style>
