const wpConfig = require("./webpack.config.js");
const webpack = require("webpack");
const compiler = webpack(wpConfig);
compiler.run((err, stats) => {
    if (err){
        console.log(err);
    } else {
        console.log("HyphyVision built successfully.");
    }
})