var element = document.getElementById("app");
var div = document.createElement('div');
div.innerText = JSON.stringify(JSON.parse(element.getAttribute("data-incoming")));
document.body.appendChild(div);