import datetime
import dash
from dash import dcc
import dash_bootstrap_components as dbc
import dash_leaflet as dl
from django_plotly_dash import DjangoDash
from django.utils.translation import gettext, gettext_lazy
import plotly.express as px
import pandas as pd
from dash_extensions.enrich import DashProxy, Input, Output, html, no_update
from dash_extensions.javascript import assign
import xyzservices
import requests
from copy import deepcopy

default_sic_date = datetime.date.today() - datetime.timedelta(days=1)

app = DjangoDash('PolarRoute')

app.layout = html.Div(
    [
        dbc.Spinner(color="primary"),
        dl.Map([
           dl.TileLayer(id="basemap", attribution=("© OpenStreetMap contributors"), zIndex=0,),
           dl.FullScreenControl(),
           dl.LayersControl([dl.Overlay(
                dl.TileLayer(
                id="amsr",
                url="https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/AMSRU2_Sea_Ice_Concentration_12km/default/"+default_sic_date.strftime("%Y-%m-%d")+"/GoogleMapsCompatible_Level6/{z}/{y}/{x}",
                attribution="Imagery provided by services from the Global Imagery Browse Services (GIBS), operated by the NASA/GSFC/Earth Science Data and Information System (<a href=\"https://earthdata.nasa.gov\">ESDIS</a>) with funding provided by NASA/HQ.",
                maxZoom=6,
                ), name="AMSR", checked=False, id="amsr-overlay")
           ], id="layers-control"),
        ], center=[-72, -67], zoom=4, style={"height": "80vh"}, id="map"),
        dcc.Slider(min=-30, max=0, step=1, value=0, id='amsr-date-slider', marks=None, tooltip={"placement": "top", "always_visible": False}),
        html.Span(id='slider-output-container'),
    ],
)

@app.callback(
        Output("amsr-overlay", "children"),
        Input("amsr-date-slider", "value"),
        prevent_initial_call=True)
def update_amsr_overlay(slider_value):
    sic_date = (default_sic_date - datetime.timedelta(days=abs(slider_value))).strftime("%Y-%m-%d")

    return dl.TileLayer(
            id="amsr",
            url="https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/AMSRU2_Sea_Ice_Concentration_12km/default/"+sic_date+"/GoogleMapsCompatible_Level6/{z}/{y}/{x}",
            attribution="Imagery provided by services from the Global Imagery Browse Services (GIBS), operated by the NASA/GSFC/Earth Science Data and Information System (<a href=\"https://earthdata.nasa.gov\">ESDIS</a>) with funding provided by NASA/HQ.",
            maxZoom=6,
            )


def server_url(request):
    "Return server url from request object in dpd callback."
    return f"{request.scheme}://{request.get_host()}"


