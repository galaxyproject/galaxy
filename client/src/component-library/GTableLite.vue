<script setup lang="ts">
import { BTableLite } from "bootstrap-vue";
</script>

<template>
    <BTableLite v-bind="$attrs" v-on="$listeners">
        <template v-slot:table-caption>
            <slot name="table-caption"></slot>
        </template>

        <template v-slot:cell()="data">
            <slot :name="`cell(${data.field.key})`" v-bind="data"></slot>
        </template>

        <slot></slot>
    </BTableLite>
</template>
