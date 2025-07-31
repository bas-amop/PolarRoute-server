import datetime
import json
import logging
import os

import dash
from dash import dcc, ALL
import dash_bootstrap_components as dbc
import dash_leaflet as dl
from django_plotly_dash import DjangoDash
from dash_extensions.enrich import Input, Output, State, html, no_update
from dash_extensions.javascript import Namespace
import requests

from .callbacks import register_callbacks
from .components import amsr_layer
from .layouts import route_request_form

FORMAT = "[%(filename)s . %(funcName)20s() ] %(message)s"
logging.basicConfig(format=FORMAT)
logger = logging.getLogger(__name__)

default_sic_date = datetime.date.today() - datetime.timedelta(days=1)

stylesheets = [
    "https://cdn.web.bas.ac.uk/bas-style-kit/0.7.3/css/bas-style-kit.min.css",
    dbc.themes.BOOTSTRAP,
]

app = DjangoDash('PolarRoute', add_bootstrap_links=True, update_title=None, external_stylesheets=stylesheets)

register_callbacks(app)

ns = Namespace("polarRoute", "mapFunctions")

favourites = {
    "bird": {"lat": -54.025, "lon": -38.044, "display_name": "Bird Island"},
    "falklands": {"lat": -51.731, "lon": -57.706, "display_name": "Falklands"},
    "halley": {"lat": -75.059, "lon": -25.840, "display_name": "Halley"},
    "rothera": {"lat": -67.764, "lon": -68.02, "display_name": "Rothera"},
    "kep": {"lat": -54.220, "lon": -36.433, "display_name": "King Edward Point"},
    "signy": {"lat": -60.720, "lon": -45.480, "display_name": "Signy"},
    "nyalesund": {"lat": 78.929, "lon": 11.928, "display_name": "Ny-Ålesund"},
    "harwich": {"lat": 51.949, "lon": 1.255, "display_name": "Harwich, UK"},
    "rosyth": {"lat": 56.017, "lon": -3.440, "display_name": "Rosyth, UK"},
}



eventHandlers = dict(
    mousemove=ns("mousemove"),
    click=ns("click"),
)



app.layout = html.Div(
    children=[
        dcc.Store(id='routes-store', data=[], storage_type="session"),
        dcc.Store(id='route-visibility-store', data=[], storage_type="session"),
        dcc.Store(id='marker-store', storage_type="memory", data={}),
        dl.Map([
           dl.TileLayer(id="basemap", attribution=("© OpenStreetMap contributors"), zIndex=0,),
           dl.FullScreenControl(),
           dl.LayersControl([dl.Overlay(amsr_layer(default_sic_date), name="AMSR", checked=False, id="amsr-overlay"),], id="layers-control"),
           dl.FeatureGroup(id="routes-fg"),
           dl.FeatureGroup(id="marker-fg", children=[]),
        ], center=[-60, -67], zoom=3, style={"height": "50vh", "cursor": "crosshair"}, id="map", eventHandlers=eventHandlers),
        html.Span(" ", id='mouse-coords-container'),
        dcc.Slider(min=-30, max=0, step=1, value=0, id='amsr-date-slider', marks=None, tooltip={"placement": "top", "always_visible": False}),
        html.Span("", id='test-output-container'),
        dbc.Row([
            dbc.Col([html.H2("Recent Routes"), dcc.Loading(html.Div(id="recent-routes-table"))], class_name="col-12 col-md-6"),
            dbc.Col([html.H2("Request Route"), html.Span("Select start and end points from dropdown or by clicking on map."), html.Div(route_request_form(favourites), id='route-request')], class_name="col-12 col-md-6"),
        ]),
        dcc.Interval(id="recent-routes-interval", interval=10000),

    ],
)
