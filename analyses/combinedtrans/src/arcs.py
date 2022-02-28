import pandas as pd
import geopandas as gpd
import pydeck as pdk

from shapely.geometry import LineString


def create_arcs(nuts_centroids, epsgs):
    vols = (
        df.groupby(["origin_nuts", "destination_nuts"])["loaded_weight_kg"]
        .sum()
        .to_frame()
    )

    vols = (
        vols.join(nuts_centroids["geometry"], on=["origin_nuts"])
        .rename(columns={"geometry": "orig_geom"})
        .join(nuts_centroids["geometry"], on=["destination_nuts"])
        .rename(columns={"geometry": "dest_geom"})
        .dropna(how="any", subset=["orig_geom", "dest_geom"])
    )

    geom = vols[["orig_geom", "dest_geom"]].apply(
        lambda x: LineString([x["orig_geom"], x["dest_geom"]]), axis=1
    )
    vols = gpd.GeoDataFrame(vols, geometry=geom).drop(
        columns=["orig_geom", "dest_geom"]
    )
    vols = vols.set_crs(epsg=epsgs["proj"]).to_crs(epsgs["world"])

    df = pd.DataFrame(
        vols.geometry.apply(
            lambda x: [x.coords[0][0], x.coords[0][1], x.coords[-1][0], x.coords[-1][1]]
        ).tolist(),
        index=vols.index,
        columns=["orig_lon", "orig_lat", "dest_lon", "dest_lat"],
    )
    df = df.join(vols["loaded_weight_kg"])

    GREEN_RGB = [0, 255, 0, 40]
    RED_RGB = [240, 100, 0, 40]

    # Specify a deck.gl ArcLayer
    arc_layer = pdk.Layer(
        "ArcLayer",
        data=df,
        get_width="loaded_weight_kg / 10000",
        get_source_position=["orig_lon", "orig_lat"],
        get_target_position=["dest_lon", "dest_lat"],
        get_tilt=15,
        get_source_color=GREEN_RGB,
        get_target_color=RED_RGB,
        pickable=True,
        auto_highlight=True,
    )

    view_state = pdk.ViewState(
        latitude=38.095071, longitude=23.394901, bearing=45, pitch=50, zoom=8,
    )

    TOOLTIP_TEXT = {
        "html": "loaded_weight_kg: {loaded_weight_kg} port origin: {origin_port} port destination: {destination_port}"
    }
    r = pdk.Deck(
        arc_layer,
        initial_view_state=view_state,
        tooltip=TOOLTIP_TEXT,
        map_style="light",
    )
    return r
