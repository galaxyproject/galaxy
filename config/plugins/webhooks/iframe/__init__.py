def main(trans, webhook, params):
    url = getattr(trans.app.config, "center_panel_url", None)
    if not url:
        return {}
    return {
        "src": url,
        "title": getattr(trans.app.config, "center_panel_title", ""),
        "height": getattr(trans.app.config, "center_panel_height", 1000),
    }
