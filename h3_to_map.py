import geopandas as gpd
import pandas as pd
import numpy as np
import json
import h3
import folium
import osmnx as ox
from shapely import wkt
# from folium.plugins import HeatMap
from shapely.geometry import Polygon

from tags import bulding_tags
from osmnx_data import get_lat_lon


def osm_query(tag, city):
    gdf = ox.geometries_from_place(city, tag).reset_index()
    gdf['type'] = np.full(len(gdf), tag[list(tag.keys())[0]])
    gdf = gdf[['type', 'geometry']]
    # print(gdf.shape)
    return gdf


def get_gdfs(city_name, class_self = None):
    print('func: get_gdfs / h3_to_map.py')
    gdfs = []
    i_size = 100/len(bulding_tags)
    for i in range(len(bulding_tags)):
        gdfs.append(osm_query(bulding_tags[i], city_name))
        # print(i)
        if class_self is not None:
            i+=i_size
            class_self.progress_bar_thread.set_i(int(i*i_size))
            class_self.progress_bar_thread.start()
    return gdfs


def get_data_poi(city_name, class_self = None):
    print('func: get_data_poi / h3_to_map.py')
    gdfs = get_gdfs(city_name, class_self)
    data_poi = pd.concat(gdfs)
    lat, lon = get_lat_lon(data_poi['geometry'])
    data_poi['lat'] = lat
    data_poi['lon'] = lon
    data_poi.groupby(['type'], as_index = False).agg({'geometry':'count'})

    return data_poi


def create_hexagons(geoJson):
    print('func: create_hexagons / h3_to_map.py')
    polyline = geoJson['coordinates'][0]

    polyline.append(polyline[0])
    lat = [p[0] for p in polyline]
    lng = [p[1] for p in polyline]
    m = folium.Map(location=[sum(lat)/len(lat), sum(lng)/len(lng)], zoom_start=13, tiles='cartodbpositron')
    my_PolyLine=folium.PolyLine(locations=polyline,weight=8,color="green")
    m.add_child(my_PolyLine)

    hexagons = list(h3.polyfill(geoJson, 8))
    polylines = []
    lat = []
    lng = []
    for hex in hexagons:
        polygons = h3.h3_set_to_multi_polygon([hex], geo_json=False)
        # flatten polygons into loops.
        outlines = [loop for polygon in polygons for loop in polygon]
        polyline = [outline + [outline[0]] for outline in outlines][0]
        lat.extend(map(lambda v:v[0],polyline))
        lng.extend(map(lambda v:v[1],polyline))
        polylines.append(polyline)
    for polyline in polylines:
        my_PolyLine=folium.PolyLine(locations=polyline,weight=3,color='red')
        m.add_child(my_PolyLine)
        
    polylines_x = []
    for j in range(len(polylines)):
        a = np.column_stack((np.array(polylines[j])[:,1],np.array(polylines[j])[:,0])).tolist()
        polylines_x.append([(a[i][0], a[i][1]) for i in range(len(a))])
        
    polygons_hex = pd.Series(polylines_x).apply(lambda x: Polygon(x))
        
    return m, polygons_hex, polylines


def hex_to_obj(polygons, polylines, city_name, data_poi = None):
    print('func: hex_to_obj / h3_to_map.py')
    if data_poi is None:
        data_poi = get_data_poi(city_name)

    gdf_1 = gpd.GeoDataFrame(data_poi, geometry=gpd.points_from_xy(data_poi.lon, data_poi.lat))

    gdf_2 = pd.DataFrame(polygons, columns = ['geometry'])
    gdf_2['polylines'] = polylines
    gdf_2['geometry'] = gdf_2['geometry'].astype(str)
    geometry_uniq = pd.DataFrame(gdf_2['geometry'].drop_duplicates())
    geometry_uniq['id'] = np.arange(len(geometry_uniq)).astype(str)
    gdf_2 = gdf_2.merge(geometry_uniq, on = 'geometry')
    gdf_2['geometry'] = gdf_2['geometry'].apply(wkt.loads)
    gdf_2 = gpd.GeoDataFrame(gdf_2, geometry='geometry')

    itog_table = gpd.sjoin(gdf_2, gdf_1, how='left', op='intersects')
    itog_table = itog_table.dropna()
    itog_table.head()
    return itog_table


def create_choropleth(data, json, columns, legend_name, feature, bins):
    print('func: create_choropleth / h3_to_map.py')
    
    lat, lon = get_lat_lon(data['geometry'])

    m = folium.Map(location=[sum(lat)/len(lat), sum(lon)/len(lon)], zoom_start=13, tiles='cartodbpositron')
    
    folium.Choropleth(
        geo_data=json,
        name="choropleth",
        data=data,
        columns=columns,
        key_on="feature.id",
        fill_color="YlGn",
        fill_opacity=0.7,
        line_opacity=0.2,
        legend_name=legend_name,
        nan_fill_color = 'black',
        bins = bins

    ).add_to(m)

    folium.LayerControl().add_to(m)

    return m


def gen_hexagons(polygon_krd, city_name, bulding_type, data_poi):
    print('func: gen_hexagons / h3_to_map.py')
    # polygon_hex , polylines - геометрии гексагонов в разных форматах
    
    # сгенерим гексагоны внутри полигона
    geoJson = json.loads(gpd.GeoSeries(polygon_krd['geometry']).to_json())
    geoJson = geoJson['features'][0]['geometry']
    geoJson = {'type':'Polygon','coordinates': [np.column_stack((np.array(geoJson['coordinates'][0])[:, 1],
                                                        np.array(geoJson['coordinates'][0])[:, 0])).tolist()]}

    m, polygons, polylines = create_hexagons(geoJson)

    # подготовим данные 
    itog_table = hex_to_obj(polygons, polylines, city_name, data_poi)

    data = np.array(itog_table)
    np.savetxt(f'city_tables/city_{city_name}.csv', data[:, -3:], delimiter=',', fmt='%s')
    print('city_table saved')
        

    itog_table['geometry'] = itog_table['geometry'].astype(str) #для groupby
    itog_table['id'] = itog_table['id'].astype(str) #для Choropleth
    agg_all = itog_table.groupby(['geometry','type','id'], as_index = False).agg({'lat':'count'}).rename(columns = {'lat':'counts'})
    agg_all['geometry'] = agg_all['geometry'].apply(wkt.loads) #возвращаем формат геометрий

    agg_all_cafe = agg_all.query(f"type == '{bulding_type}'")[["geometry","counts",'id']]
    agg_all_cafe['id'] = agg_all_cafe['id'].astype(str)
    data_geo_1 = gpd.GeoSeries(agg_all_cafe.set_index('id')["geometry"]).to_json()

    map_with_hex = create_choropleth(agg_all_cafe, data_geo_1, ["id","counts"], bulding_type+' Саны', 'counts', 5)
    return map_with_hex