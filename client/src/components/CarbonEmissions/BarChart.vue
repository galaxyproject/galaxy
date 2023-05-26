<script setup lang="ts">
import {
    Chart as ChartJS,
    Title,
    Tooltip,
    Legend,
    BarElement,
    CategoryScale,
    LinearScale,
    type ChartOptions,
} from "chart.js";
import { Bar } from "vue-chartjs";

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

defineProps<{
    data: {
        labels: string[];
        datasets: {
            label: string;
            backgroundColor: string[];
            data: number[];
        }[];
    };
}>();

const options: ChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
};
</script>

<template>
    <Bar :data="data" :options="options" />
</template>
