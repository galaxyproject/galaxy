const record = (window.__fixture = { config: null, commands: [], starts: 0 });

class ChatFixture extends HTMLElement {
  connectedCallback() {
    if (!this.started) {
      this.started = true;
      record.starts++;
      record.config = JSON.parse(this.dataset.incoming).visualization_config;
      this.addEventListener("galaxy", (event) => {
        const data = event.detail;
        if (data?.from === "galaxy") {
          record.commands.push(data);
          this.show(`${data.type}: ${data.exchange_id ?? data.question}`);
          if (data.type === "open") {
            this.report(data.exchange_id, true);
          } else if (data.type === "ask") {
            this.report(null, false);
          }
        }
      });
      this.show(`mounted: ${JSON.stringify(record.config)}`);
      this.report(record.config.exchange_id ?? null, !record.config.question);
    }
  }

  show(line) {
    const item = document.createElement("p");
    item.className = "fixture-line";
    item.textContent = line;
    this.appendChild(item);
  }

  report(exchangeId, saved) {
    const message = {
      visualization_config: { exchange_id: exchangeId },
      visualization_saved: saved,
    };
    this.dispatchEvent(
      new CustomEvent("galaxy-visualization", {
        detail: { from: "galaxy-visualization", ...message },
      }),
    );
  }
}

if (!customElements.get("chat-fixture")) {
  customElements.define("chat-fixture", ChatFixture);
}
