import datetime

import dash_bootstrap_components as dbc
from dash_extensions.enrich import html
from dash_extensions.javascript import Namespace
import dash_leaflet as dl

ns = Namespace("polarRoute", "mapFunctions")

def marker(lat:float, lon:float, loc:str="start"):

    if loc == "start":
        iconUrl = "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-green.png"
    elif loc == "end":
        iconUrl = "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-red.png"
    else:
        raise ValueError(f"Valid values of loc are 'start' and 'end', got {loc}.")

    return dl.Marker(id={"type": "marker", "index": loc}, position=[lat, lon], draggable=True, eventHandlers=dict(dragend=ns("dragend")), icon=dict(iconUrl=iconUrl, iconAnchor=[11, 40]))


def amsr_layer(date: datetime.date):
    return dl.TileLayer(
            id="amsr",
            url="https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/AMSRU2_Sea_Ice_Concentration_12km/default/"+date.strftime("%Y-%m-%d")+"/GoogleMapsCompatible_Level6/{z}/{y}/{x}",
            attribution="Imagery provided by services from the Global Imagery Browse Services (GIBS), operated by the NASA/GSFC/Earth Science Data and Information System (<a href=\"https://earthdata.nasa.gov\">ESDIS</a>) with funding provided by NASA/HQ.",
            maxZoom=6,
            )


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

