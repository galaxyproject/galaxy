<script setup lang="ts">
import { ref } from 'vue';

const tooltip = "Enable/Disable Help Mode"

//currentValue must me reactive
const currentValue = ref(false)

</script>    

<template>
    <div>
        <b-form-checkbox v-model="currentValue" class="no-highlight" switch :title="tooltip">
        </b-form-checkbox>
    </div>
</template>


