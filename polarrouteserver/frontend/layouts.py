import dash_bootstrap_components as dbc
from dash_extensions.enrich import html

from .utils import get_locations


def coords_input(loc, locations):
    return html.Div(
        [
            dbc.InputGroup(
                [
                    dbc.InputGroupText(loc),
                    dbc.Select(
                        options=[{"label": f["name"], "value": f} for f in locations],
                        id={"type": "location-select", "index": loc},
                        class_name="bsk-form-control",
                    ),
                    dbc.Input(
                        id={"type": "location-coords", "index": loc},
                        placeholder="lat, lon",
                        disabled=True,
                        class_name="bsk-form-control",
                    ),
                    dbc.Input(
                        id={"type": "location-name", "index": loc},
                        placeholder="name this location (optional)",
                        class_name="bsk-form-control",
                    ),
                ],
                class_name="bsk-input-group",
            )
        ]
    )


def route_request_form(locations: list[dict] = None):
    if not locations:
        locations = get_locations()

    return dbc.Form(
        [
            coords_input("start", locations),
            coords_input("end", locations),
            dbc.Button(
                "Submit",
                color="primary",
                id="request-button",
                class_name="bsk-btn bsk-btn-primary",
            ),
            dbc.Spinner(children=html.P(""), color="primary", id="request-spinner"),
        ]
    )
