const { root, visualization_config, visualization_plugin } = JSON.parse(document.getElementById("app").dataset.incoming);

const container = Object.assign(document.createElement("div"), {
    style: `
        font-family: sans-serif;
        max-width: 600px;
        margin: 0rem auto;
        line-height: 1.5;
        font-size: 14px;
        position: relative;
        padding: 1rem;
        background-image: url(${root + visualization_plugin.logo});
        background-size: 50px;
        background-repeat: repeat;
        background-position: center;
        opacity: 0.5;
    `
});

const content = Object.assign(document.createElement("div"), {
    style: "position: relative; z-index: 1; background: rgba(255, 255, 255, 0.9); padding: 1rem; border-radius: 0.5rem; word-wrap: break-word; overflow-wrap: break-word; word-break: break-all;"
});

const dataset = Object.assign(document.createElement("div"), {
    innerText: `You have selected dataset: ${visualization_config.dataset_id}`,
    style: "margin-bottom: 1rem; font-weight: 600;"
});
content.appendChild(dataset);

Object.entries(visualization_plugin).forEach(([key, value]) => {
    const row = Object.assign(document.createElement("div"), {
        style: "display: flex; margin-bottom: 0.25rem;"
    });
    const spanKey = Object.assign(document.createElement("span"), {
        innerText: key,
        style: "font-weight: 600; width: 150px; flex-shrink: 0;"
    });
    const spanValue = Object.assign(document.createElement("span"), {
        innerText: JSON.stringify(value),
        style: "color: #444;"
    });
    row.appendChild(spanKey);
    row.appendChild(spanValue);
    content.appendChild(row);
});

container.appendChild(content);
document.body.appendChild(container);
