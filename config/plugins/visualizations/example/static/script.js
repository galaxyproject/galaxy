var element = document.getElementById("app");
var div = document.createElement('div');
div.innerHTML = JSON.stringify(JSON.parse(element.getAttribute("data-incoming")));
document.body.appendChild(div);