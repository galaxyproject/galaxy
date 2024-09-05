const { visualization_plugin: plugin, root } = JSON.parse(document.getElementById("app").dataset.incoming);

const div = Object.assign(document.createElement("div"), {
    style: "border: 2px solid #25537b; border-radius: 1rem; padding: 1rem"
});

const img = Object.assign(document.createElement("img"), {
    src: root + plugin.logo,
    style: "height: 3rem"
});

div.appendChild(img);

Object.entries(plugin).forEach(([key, value]) => {
    const row = document.createElement("div");
    const spanKey = Object.assign(document.createElement("span"), {
        innerText: `${key}: `,
        style: "font-weight: bold"
    });
    const spanValue = Object.assign(document.createElement("span"), {
        innerText: value
    });
    row.appendChild(spanKey);
    row.appendChild(spanValue);
    div.appendChild(row);
});

document.body.appendChild(div);
