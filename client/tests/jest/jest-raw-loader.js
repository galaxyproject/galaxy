module.exports = {
    process: (content) => {
        return { code: "module.exports = " + JSON.stringify(content) };
    },
};
