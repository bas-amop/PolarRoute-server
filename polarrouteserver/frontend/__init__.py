import logging
import warnings

from dash import dcc
import dash_bootstrap_components as dbc
import dash_leaflet as dl
from django_plotly_dash import DjangoDash
from dash_extensions.enrich import html
from dash_extensions.javascript import Namespace

from .callbacks import register_callbacks
from .components import amsr_layer, header, footer, site_development_notice
from .layouts import route_request_form
from .utils import default_sic_date

logger = logging.getLogger(__name__)
FORMAT = "[%(filename)s . %(funcName)20s() ] %(message)s"
logging.basicConfig(format=FORMAT)

stylesheets = [
    "https://cdn.web.bas.ac.uk/bas-style-kit/0.7.3/css/bas-style-kit.min.css",
    dbc.themes.BOOTSTRAP,
    dbc.icons.BOOTSTRAP,
]

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    app = DjangoDash(
        "PolarRoute",
        add_bootstrap_links=True,
        update_title=None,
        external_stylesheets=stylesheets,
    )

register_callbacks(app)

ns = Namespace("polarRoute", "mapFunctions")

eventHandlers = dict(
    mousemove=ns("mousemove"),
    click=ns("click"),
)


def serve_layout():
    return html.Div(
        children=[
            dcc.Store(id="routes-store", data=[], storage_type="memory"),
            dcc.Store(id="route-visibility-store", data=[], storage_type="memory"),
            dcc.Store(id="marker-store", storage_type="memory", data={}),
            dcc.Interval(id="recent-routes-interval", interval=10000),
            # dcc.Interval(id="route-request-form-interval", interval=1, n_intervals=0, max_intervals=1),
            html.Header(header),
            site_development_notice,
            dl.Map(
                [
                    dl.TileLayer(
                        id="basemap",
                        attribution=("© OpenStreetMap contributors"),
                        zIndex=0,
                    ),
                    dl.FullScreenControl(),
                    dl.LayersControl(
                        [
                            dl.Overlay(
                                amsr_layer(default_sic_date),
                                name="AMSR",
                                checked=False,
                                id="amsr-overlay",
                            ),
                        ],
                        id="layers-control",
                    ),
                    dl.FeatureGroup(id="routes-fg"),
                    dl.FeatureGroup(id="marker-fg", children=[]),
                ],
                center=[-60, -67],
                zoom=3,
                style={"height": "50vh", "cursor": "crosshair"},
                id="map",
                eventHandlers=eventHandlers,
            ),
            html.Span(" ", id="mouse-coords-container"),
            dcc.Slider(
                min=-30,
                max=0,
                step=1,
                value=0,
                id="amsr-date-slider",
                marks=None,
                tooltip={"placement": "top", "always_visible": False},
            ),
            html.Span("", id="test-output-container"),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Row(
                                [
                                    dbc.Col(html.H2("Recent Routes"), width=4),
                                    dbc.Col(
                                        dbc.Button(
                                            html.I(
                                                className="bi bi-arrow-clockwise me-2"
                                            ),
                                            id="refresh-routes-button",
                                            class_name="bsk-btn bsk-btn-primary",
                                        )
                                    ),
                                ],
                                justify="start",
                            ),
                            dcc.Loading([html.Div(id="recent-routes-table")]),
                            html.Div(id="recent-routes-tooltips"),
                        ],
                        class_name="col-12 col-md-6",
                    ),
                    dbc.Col(
                        [
                            html.H2("Request Route"),
                            html.Span(
                                "Select start and end points from dropdown or by clicking on map."
                            ),
                            html.Div(route_request_form(), id="route-request"),
                        ],
                        class_name="col-12 col-md-6",
                    ),
                ]
            ),
            html.Footer(footer),
        ],
    )


app.layout = serve_layout
