<template>
    <div id="description">
        <div v-show="bco" class="bco-stats">
            <h2 class="domain">Description Domain</h2>
            <table v-for="object in bco.description_domain" :key="object">
                <tr>
                    <td>{{ object }}</td>
                </tr>
            </table>
        </div>
    </div>
</template>

<script>
export default {
    name: "description",
    props: ["bco"],
};
</script>
