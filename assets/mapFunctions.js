window.polarRoute = Object.assign({}, window.polarRoute, {
    mapFunctions: {
        mousemove: function(e, ctx) {
            ctx.setProps({
                mouseCoords: {
                    area: e.latlng
                }
            })
        },
        click: function(e, ctx) {

            ctx.setProps({
                n_clicks: ctx.n_clicks == undefined ? 1 : ctx.n_clicks + 1, // increment counter
                clickData: {
                    latlng: e.latlng,
                    layerPoint: e.layerPoint,
                    containerPoint: e.containerPoint
                }
            });
        },
        // marker drag end event handler
        dragend: function(e, ctx) {

            latlng = e.target.getLatLng();

            ctx.setProps({
                dragEndPosition: {
                    lat:latlng.lat,
                    lon:latlng.lng,
                }
            });
        }

    }
});