const { visualization_config, visualization_plugin, root } = JSON.parse(document.getElementById("app").dataset.incoming);

const div = Object.assign(document.createElement("div"), {
    style: "border: 2px solid #25537b; border-radius: 1rem; padding: 1rem"
});

const img = Object.assign(document.createElement("img"), {
    src: root + visualization_plugin.logo,
    style: "height: 3rem"
});
div.appendChild(img);

Object.entries(visualization_plugin).forEach(([key, value]) => {
    const row = document.createElement("div");
    const spanKey = Object.assign(document.createElement("span"), {
        innerText: `${key}: `,
        style: "font-weight: bold"
    });
    const spanValue = Object.assign(document.createElement("span"), {
        innerText: JSON.stringify(value)
    });
    row.appendChild(spanKey);
    row.appendChild(spanValue);
    div.appendChild(row);
});

const dataset = Object.assign(document.createElement("div"), {
    innerText: `You have selected dataset: ${visualization_config.dataset_id}.`,
    style: "font-weight: bold; padding-top: 1rem;"
});
div.appendChild(dataset);

document.body.appendChild(div);
