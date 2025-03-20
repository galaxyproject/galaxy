<script setup lang="ts">
import { BFormInput, BInputGroup } from "bootstrap-vue";
import { type Tuple } from "types/utilityTypes";
import { computed } from "vue";

const props = defineProps<{
    value: Date;
}>();

const emit = defineEmits<{
    (e: "input", value: Date): void;
}>();

const date = computed(() => {
    const year = props.value.getFullYear().toString().padStart(4, "0");
    const month = (props.value.getMonth() + 1).toString().padStart(2, "0");
    const day = props.value.getDate().toString().padStart(2, "0");

    return `${year}-${month}-${day}`;
});

const time = computed(() => {
    const hours = props.value.getHours().toString().padStart(2, "0");
    const minutes = props.value.getMinutes().toString().padStart(2, "0");

    return `${hours}:${minutes}`;
});

function updateDate(newDate: string) {
    const matches = newDate.match(/(\d{4})-(\d{2})-(\d{2})/);

    if (matches?.length && matches.length >= 4) {
        const [_v, year, month, day] = matches as Tuple<4, string>;

        const date = new Date(props.value);

        try {
            date.setFullYear(parseInt(year));
            date.setDate(1);
            date.setMonth(0);
            date.setMonth(parseInt(month) - 1);
            date.setDate(parseInt(day));
        } finally {
            emit("input", date);
        }
    }
}

function updateTime(newTime: string) {
    const matches = newTime.match(/(\d{2}):(\d{2})/);

    if (matches?.length && matches.length >= 3) {
        const [_v, hours, minutes] = matches as Tuple<3, string>;

        const date = new Date(props.value);

        try {
            date.setHours(parseInt(hours), parseInt(minutes));
        } finally {
            emit("input", date);
        }
    }
}
</script>

<template>
    <BInputGroup>
        <BFormInput :value="date" type="date" @input="updateDate" />
        <BFormInput :value="time" type="time" @input="updateTime" />
    </BInputGroup>
</template>
