import svgwrite

MARGIN = 5
LINE_SPACING = 15
STANDALONE_SVG_TEMPLATE = """<?xml version="1.0" standalone="no"?>
<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN"
  "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">
%s"""


class WorkflowCanvas:
    def __init__(self):
        self.canvas = svgwrite.Drawing(profile="full")

        self.connectors = []
        self.boxes = []
        self.text = []
        self.in_pos = {}
        self.out_pos = {}
        self.widths = {}
        self.max_x = 0
        self.max_y = 0
        self.max_width = 0
        self.data = []

    def finish(self, for_embed=False):
        # max_x, max_y, max_width = self.max_x, self.max_y, self.max_width
        for box in self.boxes:
            self.canvas.add(box)
        for connector in self.connectors:
            self.canvas.add(connector)
        text_style_layer = self.canvas.g(style="font-family: Helvetica, Arial, FreeSans, Sans, sans, sans-serif;")
        for text in self.text:
            text_style_layer.add(text)
        self.canvas.add(text_style_layer)
        # if we're embedding this in HTML - setup a viewbox and preserve aspect ratio
        # https://css-tricks.com/scale-svg/#aa-the-viewbox-attribute
        if for_embed:
            self.canvas.viewbox(-5, -5, self.max_x + self.max_width, self.max_y + 150)
            self.canvas.fit()
        return self.canvas

    def add_boxes(self, step_dict, width, name_fill):
        x, y = step_dict["position"]["left"], step_dict["position"]["top"]
        self.boxes.append(svgwrite.shapes.Rect((x - MARGIN, y), (width, 30), fill=name_fill, stroke="#000000"))
        box_height = (len(step_dict["data_inputs"]) + len(step_dict["data_outputs"])) * LINE_SPACING + MARGIN
        # Draw separator line.
        if len(step_dict["data_inputs"]) > 0:
            box_height += LINE_SPACING
            sep_y = y + len(step_dict["data_inputs"]) * LINE_SPACING + 40
            self.text.append(
                svgwrite.shapes.Line((x - MARGIN, sep_y), (x + width - MARGIN, sep_y), stroke=svgwrite.rgb(0, 0, 0))
            )
        # Define an input/output box.
        self.boxes.append(
            svgwrite.shapes.Rect(
                (x - MARGIN, y + 30), (width, box_height), fill="#ffffff", stroke=svgwrite.rgb(0, 0, 0)
            )
        )

    def add_text(self, module_data_inputs, module_data_outputs, step, module_name):
        left, top = step.position["left"], step.position["top"]
        x, y = left, top
        order_index = step.order_index
        max_len = len(module_name) * 1.5
        self.text.append(svgwrite.text.Text(module_name, (x, y + 20), style="font-size:14px"))
        y += 45
        count = 0
        in_pos = self.in_pos
        out_pos = self.out_pos
        for di in module_data_inputs:
            cur_y = y + count * LINE_SPACING
            if order_index not in in_pos:
                in_pos[order_index] = {}
            in_pos[order_index][di["name"]] = (x, cur_y)
            self.text.append(svgwrite.text.Text(di["label"], (x, cur_y), style="font-size:10px"))
            count += 1
            max_len = max(max_len, len(di["label"]))
        if len(module_data_inputs) > 0:
            y += LINE_SPACING
        for do in module_data_outputs:
            cur_y = y + count * LINE_SPACING
            if order_index not in out_pos:
                out_pos[order_index] = {}
            out_pos[order_index][do["name"]] = (x, cur_y)
            self.text.append(svgwrite.text.Text(do["name"], (x, cur_y), style="font-size:10px"))
            count += 1
            max_len = max(max_len, len(do["name"]))
        self.widths[order_index] = max_len * 5.5
        self.max_x = max(self.max_x, left)
        self.max_y = max(self.max_y, top)
        self.max_width = max(self.max_width, self.widths[order_index])

    def add_connection(self, step_dict, conn, output_dict):
        in_coords = self.in_pos[step_dict["id"]][conn]
        # out_pos_index will be a step number like 1, 2, 3...
        out_pos_index = output_dict["id"]
        # out_pos_name will be a string like 'o', 'o2', etc.
        out_pos_name = output_dict["output_name"]
        if out_pos_index in self.out_pos:
            # out_conn_index_dict will be something like:
            # 7: {'o': (824.5, 618)}
            out_conn_index_dict = self.out_pos[out_pos_index]
            if out_pos_name in out_conn_index_dict:
                out_conn_pos = out_conn_index_dict[out_pos_name]
            else:
                # Take any key / value pair available in out_conn_index_dict.
                # A problem will result if the dictionary is empty.
                if out_conn_index_dict:
                    key = next(iter(out_conn_index_dict.keys()))
                    out_conn_pos = self.out_pos[out_pos_index][key]
        adjusted = (out_conn_pos[0] + self.widths[output_dict["id"]], out_conn_pos[1])
        self.text.append(
            svgwrite.shapes.Circle(
                center=(out_conn_pos[0] + self.widths[output_dict["id"]] - MARGIN, out_conn_pos[1] - MARGIN),
                r=5,
                fill="#ffffff",
                stroke="#000000",
            )
        )
        marker = self.canvas.marker(
            overflow="visible",
            refX="0",
            refY="5",
            viewBox="0 0 10 5",
            markerWidth="8",
            markerHeight="10",
            markerUnits="strokeWidth",
            orient="auto",
            stroke="none",
            fill="black",
        )
        marker.add(self.canvas.path(d="M 0 0 L 10 5 L 0 10 z"))
        self.canvas.defs.add(marker)
        conn = svgwrite.shapes.Line(
            (adjusted[0], adjusted[1] - MARGIN), (in_coords[0] - 10, in_coords[1]), stroke="#000000"
        )
        conn["marker-end"] = marker.get_funciri()
        self.connectors.append(conn)

    def add_steps(self, highlight_errors=False):
        # Only highlight missing tools if displaying in the tool shed.
        for step_dict in self.data:
            tool_unavailable = step_dict.get("tool_errors", False)
            if highlight_errors and tool_unavailable:
                fill = "#EBBCB2"
            else:
                fill = "#EBD9B2"
            width = self.widths[step_dict["id"]]
            self.add_boxes(step_dict, width, fill)
            for conn, output_dict in step_dict["input_connections"].items():
                self.add_connection(step_dict, conn, output_dict)

    def populate_data_for_step(self, step, module_name, module_data_inputs, module_data_outputs, tool_errors=None):
        step_dict = {
            "id": step.order_index,
            "data_inputs": module_data_inputs,
            "data_outputs": module_data_outputs,
            "position": step.position,
        }
        if tool_errors:
            step_dict["tool_errors"] = tool_errors
        input_conn_dict = {}
        for conn in step.input_connections:
            input_conn_dict[conn.input_name] = dict(id=conn.output_step.order_index, output_name=conn.output_name)
        step_dict["input_connections"] = input_conn_dict
        self.data.append(step_dict)
        self.add_text(module_data_inputs, module_data_outputs, step, module_name)
