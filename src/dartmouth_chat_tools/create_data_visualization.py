import json
from fastapi.responses import HTMLResponse
from typing import Optional, Union, Literal
from pydantic import BaseModel, Field


class Tools:
    class UserValves(BaseModel):
        template: Literal[
            "plotly",
            "plotly_white",
            "plotly_dark",
            "ggplot2",
            "seaborn",
            "simple_white",
        ] = Field(
            default="plotly_white",
            description="Default Plotly template for visualizations",
        )
        pass

    def __init__(self):
        pass

    async def create_visualization_tool(
        self,
        title: str,
        traces: Union[dict, list[dict]],
        layout: Optional[dict] = None,
        config: Optional[dict] = None,
        __user__: Optional[dict] = None,
        __event_emitter__=None,
    ) -> HTMLResponse:
        """
        Creates an interactive data visualization to embed in the chat.
        Uses Plotly.js under-the-hood.

        When calling this tool, inform the user that it may take a while to
        generate the visualization.

        :param title: Title of the visualization
        :param traces: Single trace dict or list of trace dicts. Each trace
                       should contain plot data and configuration.
                       Common trace properties:
                       - x: list of x-axis values
                       - y: list of y-axis values
                       - type: plot type (scatter, bar, line, histogram, box,
                               heatmap, pie, etc.)
                       - mode: for scatter plots (markers, lines, lines+markers)
                       - name: trace name for legend
                       - marker: marker styling (color, size, symbol, etc.)
                       - line: line styling (color, width, dash, etc.)
                       - text: hover text
                       - hovertemplate: custom hover template
        :param layout: Optional layout configuration dict. Common properties:
                       - xaxis: x-axis configuration (title, range, type, etc.)
                       - yaxis: y-axis configuration (title, range, type, etc.)
                       - showlegend: whether to show legend (default: True)
                       - legend: legend configuration (x, y, orientation, etc.)
                       - width: plot width in pixels
                       - height: plot height in pixels
                       - margin: plot margins (l, r, t, b)
                       - grid: for subplots (rows, columns, pattern, etc.)
        :param config: Optional Plotly config dict for interactivity settings
                       - displayModeBar: show/hide mode bar
                       - displaylogo: show/hide Plotly logo
                       - modeBarButtonsToRemove: list of buttons to remove
                       - responsive: make plot responsive

        Examples:
        ---------
        Simple scatter plot:
            traces = {
                "x": [1, 2, 3, 4],
                "y": [10, 15, 13, 17],
                "type": "scatter",
                "mode": "markers"
            }

        Multiple traces:
            traces = [
                {
                    "x": [1, 2, 3, 4],
                    "y": [10, 15, 13, 17],
                    "type": "scatter",
                    "mode": "lines",
                    "name": "Series 1"
                },
                {
                    "x": [1, 2, 3, 4],
                    "y": [16, 5, 11, 9],
                    "type": "scatter",
                    "mode": "lines",
                    "name": "Series 2"
                }
            ]

        With custom layout:
            layout = {
                "xaxis": {"title": "X Axis Label"},
                "yaxis": {"title": "Y Axis Label"},
                "showlegend": True
            }
        """

        # Normalize traces to list format
        if isinstance(traces, dict):
            traces_list = [traces]
        else:
            traces_list = traces

        # Set default layout if not provided
        if layout is None:
            layout = {}

        # Add title to layout if not already present
        if "title" not in layout:
            layout["title"] = title
        if __user__ is not None:
            user_template = __user__.get("valves", {})
            layout["template"] = user_template.template

        # Set default config if not provided
        if config is None:
            config = {
                "displayModeBar": True,
                "displaylogo": False,
                "responsive": True,
            }

        # Add Dartmouth watermark to layout
        watermark_url = (
            "https://raw.githubusercontent.com/dartmouth/"
            "langchain-dartmouth/main/docs/_static/img/d-pine.png"
        )

        if "images" not in layout:
            layout["images"] = []

        # Add watermark image to bottom right corner
        layout["images"].append(
            {
                "source": watermark_url,
                "xref": "paper",
                "yref": "paper",
                "x": 0.98,
                "y": 0.02,
                "sizex": 0.1,
                "sizey": 0.1,
                "xanchor": "right",
                "yanchor": "bottom",
                "opacity": 0.3,
                "layer": "below",
            }
        )

        # Convert Python objects to JSON
        traces_json = json.dumps(traces_list)
        layout_json = json.dumps(layout)
        config_json = json.dumps(config)

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{title}</title>
            <script src="https://cdn.plot.ly/plotly-3.3.0.min.js"></script>
            <style>
                body {{
                    margin: 0;
                    padding: 0;
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI",
                                 Roboto, "Helvetica Neue", Arial, sans-serif;
                }}
                #chart {{
                    width: 100%;
                    height: 100vh;
                    min-height: 400px;
                }}
            </style>
        </head>
        <body>
            <div id="chart"></div>
            <script>
                var traces = {traces_json};
                var layout = {layout_json};
                var config = {config_json};

                Plotly.newPlot('chart', traces, layout, config);

                // Make plot responsive to window resizing
                window.addEventListener('resize', function() {{
                    Plotly.Plots.resize('chart');
                }});
            </script>
        </body>
        </html>
        """

        headers = {"Content-Disposition": "inline"}

        return HTMLResponse(content=html_content, headers=headers)
