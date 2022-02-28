import pandas as pd
import geopandas as gpd

import streamlit as st


@st.cache
def create_catchment_area(ports, nuts_centroids):
    # Identify the catchment area
    carea = ports.copy()
    carea.geometry = carea.buffer(150_000)
    return (
        gpd.sjoin(carea, nuts_centroids, predicate="contains")
        .groupby(level="id")["FID"]
        .agg(tuple)
    )
