import json

import dash_bootstrap_components as dbc
from dash_extensions.enrich import html


def coords_input(loc, favourites):
    return html.Div([
        dbc.InputGroup([
            dbc.InputGroupText(loc),
            dbc.Select(options=[{'label': v['display_name'], 'value': json.dumps(v)} for v in favourites.values()], id={"type": "location-select", "index": loc}, class_name="bsk-form-control"),
            dbc.Input(id={"type": "location-coords", "index": loc}, placeholder="lat, lon", disabled=True, class_name="bsk-form-control"),
            dbc.Input(id={"type": "location-name", "index": loc}, placeholder="name this location (optional)", class_name="bsk-form-control"),
        ], class_name="bsk-input-group")
    ])

def route_request_form(favourites):
    return dbc.Form([
        coords_input("start", favourites),
        coords_input("end", favourites),
        dbc.Button("Submit", color="primary", id="request-button"),
        dbc.Spinner(children=html.P(""), color="primary", id="request-spinner"),
    ])