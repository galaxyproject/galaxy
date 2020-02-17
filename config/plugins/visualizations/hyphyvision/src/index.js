import "hyphy-vision/dist/hyphyvision.css"
//import hyphyVision from "hyphy-vision";
const hyphyVision = require('hyphy-vision');
console.debug(hyphyVision);
window.renderHyPhyVision = hyphyVision.renderHyPhyVision;
window.render_branch_selection = hyphyVision.render_branch_selection;