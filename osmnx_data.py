import geopandas as gpd
import numpy as np
import folium
import osmnx as ox
# from folium.plugins import HeatMap


def get_regions(city_name):
    try:
        polygon_krd = ox.geometries_from_place([city_name], {'boundary':'administrative'}).reset_index()
        regions = polygon_krd['name']
        new_regions = regions.dropna().unique()
        new_regions = np.sort(new_regions)
        return new_regions, polygon_krd
    except Exception as E:
        return ['Бұл атаумен қала табылмады'], None


def get_lat_lon(geometry):
    lon = geometry.apply(lambda x: x.x if x.geom_type == 'Point' else x.centroid.x)
    lat = geometry.apply(lambda x: x.y if x.geom_type == 'Point' else x.centroid.y)
    return lat, lon


def visualize_polygons(geometry):
    lats, lons = get_lat_lon(geometry)
    m = folium.Map(location=[sum(lats)/len(lats), sum(lons)/len(lons)], zoom_start=13, tiles='cartodbpositron')

    overlay = gpd.GeoSeries(geometry).to_json()
    folium.GeoJson(overlay, name = 'boundary').add_to(m)

    return m


def show_map(city_name, region_name):
    polygon_krd = ox.geometries_from_place([city_name], {'boundary':'administrative'}).reset_index()
    polygon_krd = polygon_krd[(polygon_krd['name'] == region_name)]
    m = visualize_polygons(polygon_krd['geometry'])
    return m

