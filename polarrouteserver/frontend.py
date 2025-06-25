import datetime
import dash
from dash import dcc, html
import dash_bootstrap_components as dbc
import dash_leaflet as dl
from django_plotly_dash import DjangoDash
from django.utils.translation import gettext, gettext_lazy
import plotly.express as px
import pandas as pd
from dash_extensions.enrich import DashProxy, Input, Output, html
import xyzservices


default_sic_date = datetime.date.today() - datetime.timedelta(days=1)

basemap = dl.TileLayer(id="basemap")

app = DjangoDash('PolarRoute')
app.layout = html.Div(
    [
        dl.Map([
            basemap,
            ], center=[-72, -67], zoom=4, style={"height": "80vh"}, id="map"),
        dbc.Button("Show/Hide AMSR", id="amsr-switch", className="bsk-btn bsk-btn-default"),
        dcc.Slider(min=-30, max=0, step=1, value=0, id='amsr-date-slider', marks=None, tooltip={"placement": "top", "always_visible": False}),
        html.Span(id='slider-output-container'),
    ],
)

@app.callback(
        Output("map", "children"),
        Output('slider-output-container', 'children'),
        Input("amsr-switch", "n_clicks"),
        Input("amsr-date-slider", "value"),
        prevent_initial_call=True)
def update_amsr(n_clicks, slider_value):
    hide = n_clicks % 2 == 0
    if hide:
        maps = [basemap]
        slider_text = ""
    else:
        sic_date = (default_sic_date - datetime.timedelta(days=abs(slider_value))).strftime("%Y-%m-%d")
        maps = [
            basemap, 
            dl.TileLayer(
                id="amsr",
                url="https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/AMSRU2_Sea_Ice_Concentration_12km/default/"+sic_date+"/GoogleMapsCompatible_Level6/{z}/{y}/{x}",
                attribution="Imagery provided by services from the Global Imagery Browse Services (GIBS), operated by the NASA/GSFC/Earth Science Data and Information System (<a href=\"https://earthdata.nasa.gov\">ESDIS</a>) with funding provided by NASA/HQ.",
                maxZoom=6,
                )
            ]
        slider_text = f"{sic_date}"
    
    return maps, slider_text
