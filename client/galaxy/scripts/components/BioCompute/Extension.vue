<template>
    <div id="extension">
        <div v-show="bco" class="bco-stats">
            <h2 class="domain">Extension Domain</h2>
            <table v-for="extension in bco.extension_domain" :key="extension">
                <tr>
                    <td>{{ extension }}</td>
                </tr>
            </table>
        </div>
    </div>
</template>

<script>
export default {
    name: "extension",
    props: ["bco"],
};
</script>
