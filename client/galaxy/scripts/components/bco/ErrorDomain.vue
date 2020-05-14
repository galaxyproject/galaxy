<template>
    <div id="error-domain">
        <div v-show="bco">
            <h2 class="domain">Error Domain</h2>
            <table v-for="object in bco.error_domain" :key="object">
                <tr>
                    {{
                        object
                    }}
                </tr>
                <td><button>Edit</button></td>
            </table>
        </div>
    </div>
</template>

<script>
export default {
    name: "error-domain",
    props: ["bco"],
};
</script>
