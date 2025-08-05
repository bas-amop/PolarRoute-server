import datetime
import json

import dash
from dash import ALL
import dash_bootstrap_components as dbc
import dash_leaflet as dl
from django_plotly_dash import DjangoDash
from dash_extensions.enrich import Input, Output, State, html, no_update
import requests

from .components import amsr_layer, marker, request_status_toast
from .utils import default_sic_date, server_url, request_route


def register_callbacks(app: DjangoDash):
    @app.callback(
        Output("marker-store", "data"),
        Input({"type": "marker", "index": ALL}, "dragEndPosition"),
        Input({"type": "location-select", "index": ALL}, "value"),
        Input(
            "map", "n_clicks"
        ),  # this input order must be preserved since lower inputs are prioritised
        State("map", "clickData"),
        State("marker-store", "data"),
        prevent_initial_call=True,
    )
    def update_marker_store(
        marker_position, location_value, n_clicks, clickData, marker_data
    ):
        """Updates the marker store after one of a number of triggers."""

        if dash.callback_context.triggered == []:
            return no_update

        # TODO: also update the labels on start and end with coordinates

        trigger = dash.callback_context.triggered[0]["prop_id"]

        # if trigger is map click: e.g. [{'prop_id': 'map.n_clicks', 'value': 1}]
        if trigger == "map.n_clicks":
            lat = clickData["latlng"]["lat"]
            lon = clickData["latlng"]["lng"]

            # first click is start location, second click is end
            start_point = False if n_clicks % 2 == 0 or n_clicks == 0 else True

            marker_data.update(
                {
                    "start" if start_point else "end": {
                        "lat": lat,
                        "lon": lon,
                    }
                }
            )

        # if trigger is marker move, e.g.
        elif trigger in [
            '{"index":"start","type":"marker"}.dragEndPosition',
            '{"index":"end","type":"marker"}.dragEndPosition',
        ]:
            if marker_position == [None]:
                return no_update
            # get "start" or "end"
            loc = json.loads(
                dash.callback_context.triggered[0]["prop_id"].strip(".dragEndPosition")
            )["index"]

            idx = 0 if loc == "start" else 1
            if marker_position[idx] is None:
                return no_update
            lat = marker_position[idx]["lat"]
            lon = marker_position[idx]["lon"]

            marker_data.update(
                {
                    loc: {
                        "lat": lat,
                        "lon": lon,
                    }
                }
            )

        else:
            # if trigger is dropdown, e.g. [{'prop_id': '{"index":"start","type":"location-select"}.value', 'value': '{"lat": -67.764, "lon": -68.02, "display_name": "Rothera"}'}]
            trigger_id = json.loads(
                dash.callback_context.triggered[0]["prop_id"].strip(".value")
            )["index"]
            # print(f"location_value: {location_value}")
            if trigger_id == "start":
                location_data = json.loads(location_value[0])
            elif trigger_id == "end":
                location_data = json.loads(location_value[1])
            lat = location_data["lat"]
            lon = location_data["lon"]
            # print(trigger_id)
            marker_data.update(
                {
                    trigger_id: {
                        "lat": lat,
                        "lon": lon,
                    }
                }
            )

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

        if ts is None or marker_data == {}:
            return no_update, no_update

        markers = []
        for loc in marker_data.keys():
            markers.append(
                marker(marker_data[loc]["lat"], marker_data[loc]["lon"], loc)
            )

        if marker_data.get("start", None) is None:
            start_value = no_update
        else:
            start_value = (
                f"{marker_data['start']['lat']:.2f}, {marker_data['start']['lon']:.2f}"
            )

        if marker_data.get("end", None) is None:
            end_value = no_update
        else:
            end_value = (
                f"{marker_data['end']['lat']:.2f}, {marker_data['end']['lon']:.2f}"
            )

        return start_value, end_value

    @app.callback(
        Output("mouse-coords-container", "children"),
        Input("map", "mouseCoords"),
        prevent_initial_call=True,
    )
    def update_mouse_coords(coords):
        lat = coords["area"]["lat"]
        lon = coords["area"]["lng"]

        return f"({lat:.2f}, {lon:.2f})"

    @app.callback(
        Output("amsr-overlay", "children"),
        Input("amsr-date-slider", "value"),
        prevent_initial_call=True,
    )
    def update_amsr_overlay(slider_value):
        sic_date = default_sic_date - datetime.timedelta(days=abs(slider_value))
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
            route = [x for x in routes_data if x["id"] == r["id"]][0]
            if r.get("fuel"):
                fuel_geojson = route["json"][1][0]["features"][0]
                routes_to_show.append(
                    dl.GeoJSON(
                        data=fuel_geojson,
                        style={"color": "#379245"},
                        children=[dl.Tooltip(content="Fuel-optimised")],
                    ),
                )
            if r.get("traveltime"):
                traveltime_geojson = route["json"][0][0]["features"][0]
                routes_to_show.append(
                    dl.GeoJSON(
                        data=traveltime_geojson,
                        style={"color": "#2B8CC4"},
                        children=[dl.Tooltip(content="Traveltime-optimised")],
                    ),
                )

        return routes_to_show

    @app.callback(
        Output("route-visibility-store", "data"),
        Input(
            {"type": "route-show-checkbox", "index": ALL, "route-type": "fuel"}, "value"
        ),
        Input(
            {"type": "route-show-checkbox", "index": ALL, "route-type": "traveltime"},
            "value",
        ),
    )
    def update_route_visibility(fuel_checkbox_values, traveltime_checkbox_values):
        """When checkbox is clicked, show routes on map and update routes store."""

        # iterate checkboxes
        # e.g.
        # [{'id': {'index': 'fe3daba1-09ab-4505-bfbc-3c82d7d01ee4', 'type': 'route-show-checkbox'}, 'property': 'value', 'value': True}]
        route_visibility = []

        for i, n in enumerate(dash.callback_context.inputs_list[0]):
            route = {
                "id": n["id"]["index"],
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

        r = requests.get(server_url() + "/api/recent_routes")
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
            return [x[type] for x in route_visibility if x["id"] == route_id][0]

    @app.callback(
        Output("recent-routes-table", "children"),
        Input("routes-store", "modified_timestamp"),
        Input("refresh-routes-button", "n_clicks"),
        State("routes-store", "data"),
        State("route-visibility-store", "data"),
    )
    def update_recent_routes_table(ts, _, routes_data, route_visibility):
        """Updates recent routes table in response to changing routes store."""

        if ts is None or len(routes_data) == 0:
            return [html.Span("No routes available. Try requesting one.")]
        else:
            table_header = [
                html.Thead(
                    html.Tr(
                        [
                            html.Th("Fuel"),
                            html.Th("Time"),
                            html.Th("Start"),
                            html.Th("End"),
                            html.Th("Status"),
                        ]
                    )
                )
            ]
            rows = []
            for route in routes_data:
                rows.append(
                    html.Tr(
                        [
                            html.Td(
                                dbc.Checkbox(
                                    id={
                                        "type": "route-show-checkbox",
                                        "index": route["id"],
                                        "route-type": "fuel",
                                    },
                                    value=_get_route_visibility(
                                        route_visibility, "fuel", route["id"]
                                    ),
                                )
                            ),
                            html.Td(
                                dbc.Checkbox(
                                    id={
                                        "type": "route-show-checkbox",
                                        "index": route["id"],
                                        "route-type": "traveltime",
                                    },
                                    value=_get_route_visibility(
                                        route_visibility, "traveltime", route["id"]
                                    ),
                                )
                            ),
                            html.Td(
                                f"{route['start_name']} ({route['start_lat']:.2f}, {route['start_lon']:.2f})"
                            ),
                            html.Td(
                                f"{route['end_name']} ({route['end_lat']:.2f}, {route['end_lon']:.2f})"
                            ),
                            html.Td(f"{route['status']}"),
                        ]
                    )
                )
            table_body = [html.Tbody(rows)]

            return dbc.Table(
                table_header + table_body, bordered=True, striped=True, hover=True
            )

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
    def handle_request_route_click(
        n_clicks,
        marker_data,
        start_select,
        end_select,
        start_custom_name,
        end_custom_name,
    ):
        if n_clicks:
            if marker_data == {}:
                ret = request_status_toast("No points specified.", "Error", "warning")
                return ret
            elif marker_data.get("start", None) is None:
                return request_status_toast(
                    "Start point not specified.", "Error", "warning"
                )
            elif marker_data.get("end", None) is None:
                return request_status_toast(
                    "End point not specified.", "Warning", "warning"
                )

            start_name = start_custom_name
            end_name = end_custom_name

            response = request_route(
                url=server_url(),
                start_lat=marker_data["start"]["lat"],
                start_lon=marker_data["start"]["lon"],
                end_lat=marker_data["end"]["lat"],
                end_lon=marker_data["end"]["lon"],
                start_name=start_name,
                end_name=end_name,
                force_recalculate=False,
                mesh_id=None,
            )

            if response.status_code == 200:
                if response.json().get("info"):
                    return request_status_toast(
                        response.json().get("info")["error"], "Error", "error"
                    )

            elif response.status_code == 204:
                # message = response.data
                # update_recent_routes_store(None)
                return request_status_toast(
                    "Request submitted successfully", "Success", "primary"
                )

        return no_update
