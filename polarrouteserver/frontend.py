import datetime
import json
import os
import dash
from dash import Dash, dcc, ALL
import dash_bootstrap_components as dbc
import dash_leaflet as dl
from django_plotly_dash import DjangoDash, dash_wrapper
from django.utils.translation import gettext, gettext_lazy
import plotly.express as px
import pandas as pd
from dash_extensions.enrich import DashProxy, Input, Output, State, html, no_update, ctx, DashBlueprint, PrefixIdTransform
from dash_extensions.javascript import assign, arrow_function, Namespace
# import xyzservices
import requests
from copy import deepcopy

default_sic_date = datetime.date.today() - datetime.timedelta(days=1)

stylesheets = [
    "https://cdn.web.bas.ac.uk/bas-style-kit/0.7.3/css/bas-style-kit.min.css",
    dbc.themes.BOOTSTRAP,
]

app = DjangoDash('PolarRoute', add_bootstrap_links=True, update_title=None, external_stylesheets=stylesheets)

ns = Namespace("polarRoute", "mapFunctions")

def amsr_layer(date: datetime.date):
    return dl.TileLayer(
            id="amsr",
            url="https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/AMSRU2_Sea_Ice_Concentration_12km/default/"+date.strftime("%Y-%m-%d")+"/GoogleMapsCompatible_Level6/{z}/{y}/{x}",
            attribution="Imagery provided by services from the Global Imagery Browse Services (GIBS), operated by the NASA/GSFC/Earth Science Data and Information System (<a href=\"https://earthdata.nasa.gov\">ESDIS</a>) with funding provided by NASA/HQ.",
            maxZoom=6,
            )

def server_url():
    return "http://localhost:8000"

eventHandlers = dict(
    mousemove=ns("geoff"),
    click=ns("click"),
)

favourites = {
    "bird": {"lat": -54.025, "lon": -38.044},
    "falklands": {"lat": -51.731, "lon": -57.706},
    "halley": {"lat": -75.059, "lon": -25.840},
    "rothera": {"lat": -67.764, "lon": -68.02},
    "kep": {"lat": -54.220, "lon": -36.433},
    "signy": {"lat": -60.720, "lon": -45.480},
    "nyalesund": {"lat": 78.929, "lon": 11.928},
    "harwich": {"lat": 51.949, "lon": 1.255},
    "rosyth": {"lat": 56.017, "lon": -3.440},
}

def coords_form(loc):
    return html.Div([
        dbc.InputGroup([
            dbc.InputGroupText(loc),
            dbc.Select(options=[{'label': k, 'value': v} for k,v in favourites.items()])
        ], class_name="bsk-input-group")
    ])

form = dbc.Form([coords_form("start"), coords_form("end")])

app.layout = html.Div(
    children=[
        dl.Map([
           dl.TileLayer(id="basemap", attribution=("© OpenStreetMap contributors"), zIndex=0,),
           dl.FullScreenControl(),
           dl.LayersControl([dl.Overlay(amsr_layer(default_sic_date), name="AMSR", checked=False, id="amsr-overlay"),], id="layers-control"),
           dl.FeatureGroup(id="routes-fg"),
           dl.FeatureGroup(id="marker-fg"),
        ], center=[-40, -67], zoom=3, style={"height": "80vh", "cursor": "crosshair"}, id="map", eventHandlers=eventHandlers),
        html.Span(" ", id='mouse-coords-container'),
        dcc.Slider(min=-30, max=0, step=1, value=0, id='amsr-date-slider', marks=None, tooltip={"placement": "top", "always_visible": False}),
        html.Span("", id='test-output-container'),
        dbc.Row([
            dbc.Col([html.H2("Recent Routes"), html.Div(id="recent-routes")], class_name="col-12 col-md-6"),
            dbc.Col([html.H2("Request Route"), html.Div(form, id='route-request')], class_name="col-12 col-md-6"),
        ]),
        dcc.Interval(id="recent-routes-interval", interval=150*1000),
        dcc.Store(id='routes-store'),
        dcc.Store(id='marker-store', data='{"start_lat": null, "start_lon": null, "end_lat": null, "end_lon": null}'),
    ],
)

@app.callback(
    Output("marker-fg", "children"),
    Output("marker-store", "data"),
    Input('map', 'n_clicks'),
    State('map', 'clickData'),
    State("marker-fg", "children"),
    State("marker-store", "data"),
    prevent_initial_call=True,
    )
def place_markers(n_clicks, clickData, markers, markerData):
    lat = clickData['latlng']['lat']
    lon = clickData['latlng']['lng']

    start_point = False if n_clicks % 2 == 0 or n_clicks==0 else True

    markerCoords = json.loads(markerData)

    if start_point:
        markerCoords['start_lat'] = lat
        markerCoords['start_lon'] = lon
        return [dl.Marker(id={"type": "marker", "index": "start"}, position=[lat, lon], draggable=True, icon=dict(iconUrl="https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-green.png", iconAnchor=[11, 40]))], json.dumps(markerCoords)
    else:
        markerCoords['end_lat'] = lat
        markerCoords['end_lon'] = lon
        markers.append(dl.Marker(id={"type": "marker", "index": "end"}, position=[lat, lon], draggable=True, icon=dict(iconUrl="https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-red.png", iconAnchor=[11, 40])))
        return markers, json.dumps(markerCoords)


@app.callback(
    Output("mouse-coords-container", "children"),
    Input("map", "mouseCoords"),
    prevent_initial_call=True
)
def mouse_coords(coords):
    lat = coords["area"]["lat"]
    lon = coords["area"]["lng"]

    return f"({lat:.2f}, {lon:.2f})"

@app.callback(
        Output("amsr-overlay", "children"),
        Input("amsr-date-slider", "value"),
        prevent_initial_call=True)
def update_amsr_overlay(slider_value):
    sic_date = (default_sic_date - datetime.timedelta(days=abs(slider_value)))
    return amsr_layer(sic_date)



@app.callback(
    Output("routes-fg", "children"),
    # Output("test-output-container", "children"),
    Input({"type": "route-show-checkbox", "index": ALL}, "value"),
    State("routes-store", "data"),
    prevent_initial_call=True
)
def update_routes_on_map(checkbox_values, routes):

    # load available routes from store
    routes = json.loads(routes)

    routes_to_show = []

    # iterate checkboxes
    for i,n  in enumerate(dash.callback_context.inputs_list[0]):
        checkbox_value = checkbox_values[i]
        route_id = n['id']['index']

        route_to_show = [x for x in routes if x['id']==route_id]
        traveltime_geojson = route_to_show[0]['json'][0][0]['features'][0]
        fuel_geojson = route_to_show[0]['json'][1][0]['features'][0]


        if checkbox_value == True:
            routes_to_show.extend(
                [
                    dl.GeoJSON(data=traveltime_geojson, style={'color': '#2B8CC4'}, children=[dl.Tooltip(content="Traveltime-optimised")]),
                    dl.GeoJSON(data=fuel_geojson, style={'color': '#379245'}, children=[dl.Tooltip(content="Fuel-optimised")]),
                    ]
            )

    return routes_to_show
    



@app.callback(
        Output("recent-routes", "children"),
        Output("routes-store", "data"),
        Input("recent-routes-interval", "n_intervals"),
)
def update_recent_routes_table(_):
    r = requests.get(server_url()+"/api/recent_routes")
    result = r.json()

    if len(result) == 0:
        return [html.Span("No routes available. Try requesting one.")], json.dumps(result)
    else:
        table_header = [html.Thead(
                        html.Tr([
                            html.Th(""),
                            html.Th("Start"),
                            html.Th("End"),
                            html.Th("Status"),
                        ]))]
        rows = []
        for route in result:
            rows.append(
                html.Tr([
                    html.Td(dbc.Checkbox(id={"type": "route-show-checkbox", "index": route['id']})),
                    html.Td(f"{route['start_name']} ({route['start_lat']}, {route['start_lon']})"),
                    html.Td(f"{route['end_name']} ({route['end_lat']}, {route['end_lon']})"),
                    html.Td(f"{route['status']}"),
                    ]))
        table_body = [html.Tbody(rows)]

        return dbc.Table(table_header + table_body, bordered=True, striped=True, hover=True), json.dumps(result)


# @app.callback(
#     Output("slider-output-container", "children"),
#     Input({"type": "route-checkbox", "index": ALL}, "value"),
# )
# def display_output(values):
#     return str(values)


def get_route_geojson(route: dict):
    return route['json'][0][0]
