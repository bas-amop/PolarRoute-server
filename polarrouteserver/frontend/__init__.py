import datetime
import json
import logging
import os

import dash
from dash import dcc, ALL
import dash_bootstrap_components as dbc
import dash_leaflet as dl
from django_plotly_dash import DjangoDash
from dash_extensions.enrich import Input, Output, State, html, no_update,
from dash_extensions.javascript import Namespace
import requests

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
    return os.getenv("POLARROUTE_FRONTEND_INTERNAL_URL", "http://localhost:8000")

def request_status_toast(content, header, icon, is_open=True, duration=5000):

    return dbc.Toast(
            [html.P(content, className="mb-0")],
            id="request-status-toast",
            header=header,
            icon=icon,
            dismissable=True,
            is_open=is_open,
            duration=duration,
        )

def _summarise_route(route):
    
    keys_to_extract = ['id', 'start_lat', 'start_lon', 'end_lat', 'end_lon', 'start_name', 'end_name', 'show', 'mesh']
    return dict(filter(lambda item: item[0] in keys_to_extract, route.items()))

def _summarise_route_list(routes):
    summary = []
    for route in routes:
        summary.append(_summarise_route(route))
    return summary

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
            dbc.Select(options=[{'label': v['display_name'], 'value': json.dumps(v)} for v in favourites.values()], id={"type": "location-select", "index": loc}, class_name="bsk-form-control"),
            dbc.Input(id={"type": "location-coords", "index": loc}, placeholder="lat, lon", disabled=True, class_name="bsk-form-control"),
            dbc.Input(id={"type": "location-name", "index": loc}, placeholder="name this location (optional)", class_name="bsk-form-control"),
        ], class_name="bsk-input-group")
    ])

form = dbc.Form([
    coords_input("start"),
    coords_input("end"),
    dbc.Button("Submit", color="primary", id="request-button"),
    dbc.Spinner(children=html.P(""), color="primary", id="request-spinner"),
    ])

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
            dbc.Col([html.H2("Request Route"), html.Span("Select start and end points from dropdown or by clicking on map."), html.Div(form, id='route-request')], class_name="col-12 col-md-6"),
        ]),
        dcc.Interval(id="recent-routes-interval", interval=10000),

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
    """Updates the marker store after one of a number of triggers."""

    if dash.callback_context.triggered == []:
        return no_update
    
    #TODO: also update the labels on start and end with coordinates
    
    trigger = dash.callback_context.triggered[0]['prop_id']
    
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

        if marker_position == [None]:
            return no_update
        # get "start" or "end"
        loc = json.loads(dash.callback_context.triggered[0]['prop_id'].strip('.dragEndPosition'))['index']

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
    """Updates the marker positions shown on the map following a change to the marker store."""

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
    """Updates the coordinates text boxes after a change to the marker store."""

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
    Input("route-visibility-store", "modified_timestamp"),
    State("route-visibility-store", "data"),
    State("routes-store", "data"),
)
def update_map_routes(ts, route_visibility, routes_data):
    routes_to_show = []

    if ts is None:
        return no_update

    for r in route_visibility:
        route = [x for x in routes_data if x["id"]==r["id"]][0]
        if r.get("fuel"):
            fuel_geojson = route['json'][1][0]['features'][0]
            routes_to_show.append(
                    dl.GeoJSON(data=fuel_geojson, style={'color': '#379245'}, children=[dl.Tooltip(content="Fuel-optimised")]),
                )
        if r.get("traveltime"):
            traveltime_geojson = route['json'][0][0]['features'][0]
            routes_to_show.append(
                    dl.GeoJSON(data=traveltime_geojson, style={'color': '#2B8CC4'}, children=[dl.Tooltip(content="Traveltime-optimised")]),
                )
        
    return routes_to_show


@app.callback(
    Output("route-visibility-store", "data"),
    Input({"type": "route-show-checkbox", "index": ALL, "route-type": "fuel"}, "value"),
    Input({"type": "route-show-checkbox", "index": ALL, "route-type": "traveltime"}, "value"),
)
def update_route_visibility(fuel_checkbox_values, traveltime_checkbox_values):
    """When checkbox is clicked, show routes on map and update routes store."""

    # iterate checkboxes
    # e.g.
    # [{'id': {'index': 'fe3daba1-09ab-4505-bfbc-3c82d7d01ee4', 'type': 'route-show-checkbox'}, 'property': 'value', 'value': True}]
    route_visibility = []

    for i,n in enumerate(dash.callback_context.inputs_list[0]):
        route = {
                "id": n['id']['index'],
                "fuel": fuel_checkbox_values[i],
                "traveltime": traveltime_checkbox_values[i],
            }
            
        route_visibility.append(route)

    return route_visibility
    

@app.callback(
        Output("routes-store", "data"),
        Input("recent-routes-interval", "n_intervals"),
        State("routes-store", "data"),
)
def update_routes_store(_, existing_routes_data):
    """Requests recent routes and updates routes store."""

    r = requests.get(server_url()+"/api/recent_routes")
    new_routes_data = r.json()


    if len(existing_routes_data) == 0:
        # if there is no existing route data, use the new route data
        routes_data = []
        for route in new_routes_data:
            routes_data.append(route)
        
    else:
        
        # update routes data with any new routes
        routes_data = existing_routes_data
        existing_route_ids = [r["id"] for r in existing_routes_data]
        for route in new_routes_data:
            if route["id"] not in existing_route_ids:
                routes_data.insert(0, route)
    
        # remove any expired routes
        new_route_ids = [r["id"] for r in new_routes_data]
        for i, route in enumerate(routes_data):
            if route["id"] not in new_route_ids:
                routes_data.pop(i)

    return routes_data

def _get_route_visibility(route_visibility, type, route_id):

    if len(route_visibility) == 0:
        return False
    else:
        return [x[type] for x in route_visibility if x["id"]==route_id][0]

@app.callback(
        Output("recent-routes-table", "children"),
        Input("routes-store", "modified_timestamp"),
        State("routes-store", "data"),
        State("route-visibility-store", "data"),
)
def update_recent_routes_table(ts, routes_data, route_visibility):
    """Updates recent routes table in response to changing routes store."""

    if ts is None or len(routes_data) == 0:
        return [html.Span("No routes available. Try requesting one.")]
    else:
        
        table_header = [html.Thead(
                        html.Tr([
                            html.Th("Fuel"),
                            html.Th("Time"),
                            html.Th("Start"),
                            html.Th("End"),
                            html.Th("Status"),
                        ]))]
        rows = []
        for route in routes_data:
            rows.append(
                html.Tr([
                    html.Td(dbc.Checkbox(id={"type": "route-show-checkbox", "index": route['id'], "route-type": "fuel"}, value=_get_route_visibility(route_visibility, "fuel", route["id"]))),
                    html.Td(dbc.Checkbox(id={"type": "route-show-checkbox", "index": route['id'], "route-type": "traveltime"}, value=_get_route_visibility(route_visibility, "traveltime", route["id"]))),
                    html.Td(f"{route['start_name']} ({route['start_lat']:.2f}, {route['start_lon']:.2f})"),
                    html.Td(f"{route['end_name']} ({route['end_lat']:.2f}, {route['end_lon']:.2f})"),
                    html.Td(f"{route['status']}"),
                    ]))
        table_body = [html.Tbody(rows)]

        return dbc.Table(table_header + table_body, bordered=True, striped=True, hover=True)
    

@app.callback(
    Output("request-spinner", "children"),
    Input("request-button", "n_clicks"),
    State("marker-store", "data"),
    State({"type": "location-select", "index": "start"}, "value"),
    State({"type": "location-select", "index": "end"}, "value"),
    State({"type": "location-name", "index": "start"}, "value"),
    State({"type": "location-name", "index": "end"}, "value"),
    prevent_initial_call=True,
)
def handle_request_route_click(n_clicks, marker_data, start_select, end_select, start_custom_name, end_custom_name):

    if n_clicks:
        if marker_data == {}:
            ret = request_status_toast("No points specified.", "Error", "warning")
            return ret
        elif marker_data.get("start", None) is None:
            return request_status_toast("Start point not specified.", "Error", "warning")
        elif marker_data.get("end", None) is None:
            return request_status_toast("End point not specified.", "Warning", "warning")

        start_name = start_custom_name
        end_name = end_custom_name

        response = request_route(
            url=server_url(),
            start_lat = marker_data["start"]["lat"],
            start_lon = marker_data["start"]["lon"],
            end_lat = marker_data["end"]["lat"],
            end_lon = marker_data["end"]["lon"],
            start_name=start_name,
            end_name=end_name,
            force_recalculate=False,
            mesh_id=None,
        )

        if response.status_code == 200:
            if response.json().get("info"):
                return request_status_toast(response.json().get("info")["error"], "Error", "error")

        elif response.status_code == 204:
            # message = response.data
            # update_recent_routes_store(None)
            return request_status_toast("Request submitted successfully", "Success", "primary")

    return no_update

def request_route(
        url: str,
        start_lat: float,
        start_lon: float,
        end_lat: float,
        end_lon: float,
        start_name: str = None,
        end_name: str = None,
        mesh_id: int = None,
        force_recalculate: bool = False,
    ) -> requests.Response:

    response = requests.post(
        url=url+"/api/route",
        data={
            "start_lat": float(start_lat),
            "start_lon": float(start_lon),
            "end_lat": float(end_lat),
            "end_lon": float(end_lon),
            "start_name": start_name,
            "end_name": end_name,
            "mesh_id": mesh_id,
            "force_recalculate": force_recalculate,
        }
        )
    
    return response

def get_route_geojson(route: dict):
    return route['json'][0][0]
