<template>
    <div id=bco-header>
        <table>
            <tr>
                <td>
                    <b>Object ID</b>
                </td>
                <td class='bold_except'>
                    {{ objectid }}
                </td>
            </tr>
            <tr>
                <td>
                    <b>e-Tag</b>
                </td>
                <td>
                    {{ etag }}
                </td>
            </tr>
            <tr>
                <td>
                    <b>Spec Version</b>
                </td>
                <td>
                    {{ specversion }}
                </td>
            </tr>
        </table>
    </div>
</template>

<script>

export default {

    props: {
        objectid: String,
        etag: String,
        specversion: String
    }
    
};

</script>
