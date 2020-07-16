<template>
    <div id="parametric">
        <div v-show="bco" class="bco-stats">
            <h2 class="domain">Parametric Domain</h2>
            <table v-for="object in bco.parametric_domain" :key="object">
                <tr>
                    <td>{{ object.step }}</td>
                    <td>{{ object.param }}</td>
                    <td>{{ object.value }}</td>
                </tr>
            </table>
        </div>
    </div>
</template>

<script>
export default {
    name: "parametric",
    props: ["bco"],
};
</script>
