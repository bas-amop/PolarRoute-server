import dash
from dash import dcc, html
import dash_leaflet as dl
from django_plotly_dash import DjangoDash
from django.utils.translation import gettext, gettext_lazy
import plotly.express as px
import pandas as pd
from dash_extensions.enrich import DashProxy, Input, Output, html

app = DjangoDash('PolarRoute')
app.layout = html.Div(
    [
        dl.Map([dl.TileLayer()], center=[56, 10], zoom=6, style={"height": "50vh"}, id="map"),
    ]
)

if __name__ == "__main__":
    app.run()