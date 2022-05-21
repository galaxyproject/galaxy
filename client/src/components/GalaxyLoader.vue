<template>
    <div
        class="galaxy-loader"
        :class="[`galaxy-loader_${variant}`, { 'galaxy-loader_center': center }]"
        :style="{ transform: `scale(${size / 100})` }">
        <div class="galaxy-loader_strip-1"></div>
        <div class="galaxy-loader_strip-2"></div>
        <div class="galaxy-loader_strip-3"></div>
    </div>
</template>

<script>
export default {
    props: {
        variant: {
            type: String,
            default: "light",
        },
        size: {
            type: Number,
            default: 100,
        },
        center: {
            type: Boolean,
            default: false,
        },
    },
};
</script>

<style>
.galaxy-loader.galaxy-loader_center {
    position: absolute;
    top: 0;
    bottom: 0;
    left: 0;
    right: 0;
    margin: auto;
}

.galaxy-loader {
    display: inline-block;
    width: 100px;
    height: 100px;
    border-radius: 50px;
    position: relative;
    overflow: hidden;
}

.galaxy-loader_light {
    background-color: transparent;
    border: 2px solid #58585a;
    box-sizing: border-box;
}

.galaxy-loader_dark {
    background-color: #2c3143;
    border: 2px solid #2c3143;
    box-sizing: border-box;
}

.galaxy-loader_eu {
    background-color: transparent;
    border: 2px solid #063591;
    box-sizing: border-box;
}

.galaxy-loader > div {
    background-color: rgba(255, 0, 0, 0.3);
    display: block;
    height: 18px;
    position: absolute;
    border-radius: 2px;

    -webkit-animation: galaxy-loader_animation 1.2s infinite ease-in-out;
    animation: galaxy-loader_animation 1.2s infinite ease-in-out;
}

.galaxy-loader > .galaxy-loader_strip-1 {
    top: 16px;
    left: 13px;
    width: 59px;

    -webkit-animation-delay: -1.2s;
    animation-delay: -1.2s;
}

.galaxy-loader > .galaxy-loader_strip-2 {
    top: 39px;
    left: 13px;
    width: 44px;

    -webkit-animation-delay: -1.1s;
    animation-delay: -1.1s;
}

.galaxy-loader > .galaxy-loader_strip-3 {
    top: 61px;
    left: 25px;
    width: 59px;

    -webkit-animation-delay: -1s;
    animation-delay: -1s;
}

.galaxy-loader_light > .galaxy-loader_strip-1,
.galaxy-loader_light > .galaxy-loader_strip-2 {
    background-color: #58585a;
}

.galaxy-loader_light > .galaxy-loader_strip-3 {
    background: linear-gradient(to right, rgba(207, 188, 59, 1), rgba(207, 188, 59, 1) 20%, rgba(207, 188, 59, 0) 100%);
}

.galaxy-loader_dark > .galaxy-loader_strip-1,
.galaxy-loader_dark > .galaxy-loader_strip-2 {
    background-color: white;
}

.galaxy-loader_dark > .galaxy-loader_strip-3 {
    background: linear-gradient(to right, rgba(207, 188, 59, 1), rgba(207, 188, 59, 1) 20%, rgba(207, 188, 59, 0) 100%);
}

.galaxy-loader_eu > .galaxy-loader_strip-1,
.galaxy-loader_eu > .galaxy-loader_strip-2 {
    background-color: #063591;
}

.galaxy-loader_eu > .galaxy-loader_strip-3 {
    background: linear-gradient(to right, rgba(207, 188, 59, 1), rgba(207, 188, 59, 1) 20%, rgba(207, 188, 59, 0) 100%);
}

@-webkit-keyframes galaxy-loader_animation {
    0%,
    60%,
    100% {
        -webkit-transform: scaleX(1);
    }
    20% {
        -webkit-transform: scaleX(0.8);
    }
    40% {
        -webkit-transform: scaleX(1.2);
    }
}

@keyframes galaxy-loader_animation {
    0%,
    60%,
    100% {
        transform: scaleX(1);
        -webkit-transform: scaleX(1);
    }
    20% {
        transform: scaleX(0.8);
        -webkit-transform: scaleX(0.8);
    }
    40% {
        transform: scaleX(1.2);
        -webkit-transform: scaleX(1.2);
    }
}
</style>
