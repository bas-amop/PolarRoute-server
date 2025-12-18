CREATE OR REPLACE FUNCTION public.get_mesh_zxy(z integer, x integer, y integer, query_params json)
 RETURNS bytea
 LANGUAGE plpgsql
 IMMUTABLE PARALLEL SAFE STRICT
AS $$
DECLARE
    mvt bytea;
BEGIN
-- TODO handle reprojection/transform for arbitrary srid
    SELECT INTO mvt ST_AsMVT(tile, 'get_mesh_zxy', 4096, 'geometry')
    FROM (
        SELECT
            ST_AsMVTGeom(
                geometry,
                ST_TileEnvelope(z, x, y),
                4096, 64, true) AS geometry,
            properties
        FROM
            route_api_meshpolygon
        WHERE
            geometry && ST_TileEnvelope(z, x, y) AND
            mesh_id = (query_params->>'mesh_id')::int
    ) AS tile
    WHERE geometry IS NOT NULL;

    RETURN mvt;
END
$$
;