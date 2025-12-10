"""
requirements: plotly
"""

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from typing import Optional, Literal
from pydantic import BaseModel, Field

from fastapi.responses import HTMLResponse


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

    async def get_metadata(self, __user__, __metadata__):
        with open(__metadata__["files"][0]["file"]["path"]) as f:
            content = f.read()
        return content

    async def create_visualization_tool(
        self,
        title: str,
        plot_type: str,
        x: str,
        y: str,
        color: Optional[str] = None,
        data_transformation: Optional[str] = None,
        layout: Optional[dict] = None,
        config: Optional[dict] = None,
        __user__: Optional[dict] = None,
        __metadata__=None,
        __event_emitter__=None,
    ) -> str:
        """
        Creates an interactive data visualization using Plotly Python.
        The data is loaded automatically from the context and does not need to be
        specified. It is internally available in a pandas DataFrame called 'df'.

        If data transformation are necessary to achieve the desired visualization, you
        can provide them as pandas code on top of 'df' in 'data_transformation'.

        When calling this tool, inform the user that it may take a while to
        generate the visualization.

        :param title: Title of the visualization
        :param plot_type: Type of plot to create (scatter, bar, line, histogram, box,
                         heatmap, pie, etc.). Can also be plotly express function names
                         like 'scatter', 'bar', 'line', 'histogram', 'box', etc.
        :param x: Name of the column to use for the x-axis
        :param y: Name of the column to use for the y-axis
        :param color: Name of the column to use for coloring the marks
        :param data_transformation: Optional Python code string to transform the loaded
                                   dataframe. The dataframe will be available as the variable 'df'.
                                   Do not include imports or data loading code here.
                                   Example: "df = df.groupby('category').mean()"
        :param layout: Optional layout configuration dict for customizing the plot
                      appearance
        :param config: Optional Plotly config dict for interactivity settings
        :param __metadata__: Metadata containing file path information

        Examples:
        ---------
        Simple scatter plot:
            plot_type = "scatter"
            data_transformation = "df['x'] = df.index; df['y'] = df['value']"

        Bar chart with grouping:
            plot_type = "bar"
            data_transformation = "df = df.groupby('category')['value'].sum().reset_index()"

        Histogram:
            plot_type = "histogram"
            data_transformation = "df = df[df['value'] > 0]"  # Filter data
        """

        # Load data from file path specified in metadata
        if (
            __metadata__ is None
            or "files" not in __metadata__
            or not __metadata__["files"]
        ):
            raise ValueError("Please upload a file!")

        # Get the first file from the files list
        file_info = __metadata__["files"][0]
        file_path = file_info["file"]["path"]

        try:
            # Load data using pandas
            if file_path.endswith(".csv"):
                df = pd.read_csv(file_path)
            elif file_path.endswith((".xlsx", ".xls")):
                df = pd.read_excel(file_path)
            elif file_path.endswith(".json"):
                df = pd.read_json(file_path)
            elif file_path.endswith(".parquet"):
                df = pd.read_parquet(file_path)
            else:
                # Try to infer format or default to CSV
                df = pd.read_csv(file_path)
        except Exception as e:
            raise ValueError(f"Failed to load data from {file_path}: {str(e)}")

        # Apply data transformation if provided
        if data_transformation:
            try:
                # Create a namespace with df and pd available
                namespace = {"df": df, "pd": pd}
                # Execute the transformation code
                exec(data_transformation, namespace)
                # Get the potentially modified dataframe from the namespace
                df = namespace["df"]
            except Exception as e:
                raise ValueError(f"Failed to apply data transformation: {str(e)}")

        # Create the plot using plotly express or graph objects
        try:
            if hasattr(px, plot_type):
                # Use plotly express
                plot_func = getattr(px, plot_type)

                # Try to automatically map common column names
                kwargs = {}
                kwargs["x"] = x
                kwargs["y"] = y
                kwargs["color"] = color

                fig = plot_func(df, title=title, **kwargs)
            else:
                # Fallback to basic scatter plot with graph objects
                fig = go.Figure()
                if len(df.columns) >= 2:
                    fig.add_trace(
                        go.Scatter(
                            x=df.iloc[:, 0],
                            y=df.iloc[:, 1],
                            mode="markers",
                            name=f"{df.columns[0]} vs {df.columns[1]}",
                        )
                    )
                fig.update_layout(title=title)
        except Exception as e:
            raise ValueError(f"Failed to create plot of type '{plot_type}': {str(e)}")

        # Apply custom layout if provided
        if layout:
            fig.update_layout(**layout)

        # Apply user template if available
        if __user__ is not None:
            user_valves = __user__.get("valves", {})
            if hasattr(user_valves, "template"):
                fig.update_layout(template=user_valves.template)

        # Add Dartmouth watermark
        watermark_url = (
            "https://raw.githubusercontent.com/dartmouth/"
            "langchain-dartmouth/main/docs/_static/img/d-pine.png"
        )

        fig.add_layout_image(
            dict(
                source=watermark_url,
                xref="paper",
                yref="paper",
                x=0.98,
                y=0.02,
                sizex=0.1,
                sizey=0.1,
                xanchor="right",
                yanchor="bottom",
                opacity=0.3,
                layer="below",
            )
        )

        # Set default config if not provided
        if config is None:
            config = {
                "displayModeBar": True,
                "displaylogo": False,
                "responsive": True,
            }

        # Return HTML string using plotly's to_html function
        html_content = "<!DOCTYPE html>\n" + fig.to_html(
            include_plotlyjs=True, config=config, div_id="chart"
        )

        headers = {"Content-Disposition": "inline"}
        return HTMLResponse(content=html_content, headers=headers)
