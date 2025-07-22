import datetime
import json
import logging
import os
import dash
from dash import Dash, dcc, ALL, MATCH
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

FORMAT = "[%(filename)s . %(funcName)20s() ] %(message)s"
logging.basicConfig(format=FORMAT)
logger = logging.getLogger(__name__)

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
    mousemove=ns("mousemove"),
    click=ns("click"),
)

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

def coords_input(loc):
    return html.Div([
        dbc.InputGroup([
            dbc.InputGroupText(loc),
            dbc.Select(options=[{'label': v['display_name'], 'value': json.dumps(v)} for v in favourites.values()], id={"type": "location-select", "index": loc}),
            dbc.Input(id={"type": "location-coords", "index": loc}, placeholder="lat, lon", disabled=True)
        ], class_name="bsk-input-group")
    ])

form = dbc.Form([coords_input("start"), coords_input("end")])

app.layout = html.Div(
    children=[
        dcc.Store(id='routes-store'),
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
            dbc.Col([html.H2("Recent Routes"), dcc.Loading(html.Div(id="recent-routes"))], class_name="col-12 col-md-6"),
            dbc.Col([html.H2("Request Route"), html.Span("Select start and end points from dropdown or by clicking on map."), html.Div(form, id='route-request')], class_name="col-12 col-md-6"),
        ]),
        dcc.Interval(id="recent-routes-interval", interval=150*1000),

    ],
)

def marker(lat:float, lon:float, loc:str="start"):

    if loc == "start":
        iconUrl = "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-green.png"
    elif loc == "end":
        iconUrl = "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-red.png"
    else:
        raise ValueError(f"Valid values of loc are 'start' and 'end', got {loc}.")

    return dl.Marker(id={"type": "marker", "index": loc}, position=[lat, lon], draggable=True, eventHandlers=dict(dragend=ns("dragend")), icon=dict(iconUrl=iconUrl, iconAnchor=[11, 40]))





@app.callback(
    Output("marker-store", "data"),
    Input({"type": "marker", "index": ALL}, "dragEndPosition"),
    Input({"type": "location-select", "index": ALL}, "value"),
    Input('map', 'n_clicks'), # this input order must be preserved since lower inputs are prioritised
    State('map', 'clickData'),
    State("marker-store", "data"),
    prevent_initial_call=True
)
def update_marker_store(marker_position, location_value, n_clicks, clickData, marker_data):
    
    logger.debug(f"dash.callback_context.triggered: {dash.callback_context.triggered}")
    logger.debug(f"marker_position: {marker_position}")
    logger.debug(f"location_value: {location_value}")
    logger.debug(f"n_clicks: {n_clicks}")


    if dash.callback_context.triggered == []:
        return no_update
    
    #TODO: trigger this on marker drag too

    #TODO: also update the labels on start and end with coordinates
    
    trigger = dash.callback_context.triggered[0]['prop_id']
    logger.debug(f"trigger: {trigger}")
    logger.debug(f"type: {type(trigger)}")
    
    # if trigger is map click: e.g. [{'prop_id': 'map.n_clicks', 'value': 1}]
    if trigger == 'map.n_clicks':
        lat = clickData['latlng']['lat']
        lon = clickData['latlng']['lng']

        # first click is start location, second click is end
        start_point = False if n_clicks % 2 == 0 or n_clicks==0 else True

        marker_data.update({
            "start" if start_point else "end": {
                "lat": lat,
                "lon": lon,
            }
        })

    # if trigger is marker move, e.g.
    elif trigger in ['{"index":"start","type":"marker"}.dragEndPosition', '{"index":"end","type":"marker"}.dragEndPosition']:
        logger.debug("marker move trigger")
        logger.debug(f"marker_position: {marker_position}")

        if marker_position == [None]:
            return no_update
        # get "start" or "end"
        loc = json.loads(dash.callback_context.triggered[0]['prop_id'].strip('.dragEndPosition'))['index']
        logger.debug(f"loc: {loc}")

        idx = 0 if loc=="start" else 1
        if marker_position[idx] == None:
            return no_update
        lat = marker_position[idx]["lat"]
        lon = marker_position[idx]["lon"]

        marker_data.update({
            loc: {
                "lat": lat,
                "lon": lon,
            }
        })
    
    else:
        # if trigger is dropdown, e.g. [{'prop_id': '{"index":"start","type":"location-select"}.value', 'value': '{"lat": -67.764, "lon": -68.02, "display_name": "Rothera"}'}]
        trigger_id = json.loads(dash.callback_context.triggered[0]['prop_id'].strip('.value'))['index']
        # print(f"location_value: {location_value}")
        if trigger_id == "start":
            location_data = json.loads(location_value[0])
        elif trigger_id == "end":
            location_data = json.loads(location_value[1])
        lat = location_data["lat"]
        lon = location_data["lon"]
        # print(trigger_id)
        marker_data.update({
            trigger_id: {
                "lat": lat,
                "lon": lon,
            }
        })

    # print(marker_data)
    return marker_data


@app.callback(
    Output("marker-fg", "children"),
    Input("marker-store", "modified_timestamp"),
    State("marker-store", "data"),
)
def update_markers(ts, marker_data):
    if ts is None:
        return no_update
    
    markers = []
    for loc in marker_data.keys():
        markers.append(
            marker(marker_data[loc]["lat"], marker_data[loc]["lon"], loc)
        )
    return markers

@app.callback(
    Output({"type": "location-coords", "index": "start"}, "value"),
    Output({"type": "location-coords", "index": "end"}, "value"),
    Input("marker-store", "modified_timestamp"),
    State("marker-store", "data"),
)
def update_coords(ts, marker_data):
    if ts is None or marker_data is {}:
        return no_update, no_update
    
    markers = []
    for loc in marker_data.keys():
        markers.append(
            marker(marker_data[loc]["lat"], marker_data[loc]["lon"], loc)
        )

    if marker_data.get("start", None) is None:
        start_value = no_update
    else:
        start_value = f"{marker_data['start']['lat']:.2f}, {marker_data['start']['lon']:.2f}"
        
    if marker_data.get("end", None) is None:
        end_value = no_update
    else:
        end_value = f"{marker_data['end']['lat']:.2f}, {marker_data['end']['lon']:.2f}"

    return start_value, end_value


@app.callback(
    Output("mouse-coords-container", "children"),
    Input("map", "mouseCoords"),
    prevent_initial_call=True
)
def update_mouse_coords(coords):
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
