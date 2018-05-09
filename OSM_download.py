# example : python OSM_download.py --amenity "school" --lon 9.173196 --lat 45.478062 --dist 100

import click
from shapely.geometry import Polygon, mapping, Point
from osmnx import bbox_from_point, core
import numpy as np

class OSM_downloader:
    """
    returns the number of amenities from OSM in the given range. use:
    OSM = OSM_downloader(lat, lon, dist)
    points = OSM.query_osm('school')
    """
    def __init__(self, lat, lon, dist):

        self.north, self.south, self.east, self.west = bbox_from_point(point=(lat, lon), distance=dist)
        self.AOI = mapping(Polygon([(self.east, self.south), (self.west, self.south),
                                    (self.west, self.north), (self.east, self.north)]))

    def query_osm(self, amenity):

        query = ('[out:json][timeout:25];'
                 '('
                 'node["amenity"="{amenity:}"]({south:.8f},{west:.8f},{north:.8f},{east:.8f});'
                 'way["amenity"="{amenity:}"]({south:.8f},{west:.8f},{north:.8f},{east:.8f});'
                 ');out count;').format(amenity=amenity, north=self.north, south=self.south, east=self.east, west=self.west)

        response = core.overpass_request(data={'data': query}, timeout=600, error_pause_duration=None)
        
        if response['elements'][0]['type'] == 'count':

            return response['elements'][0]['tags']['total']


@click.command()
@click.option('--amenity', default="school")
@click.option('--lat', default=45.479012, type=float)
@click.option('--lon', default=9.169201, type=float)
@click.option('--dist', default=500)
def OSM_scraper(amenity, lat, lon, dist):

    OSM = OSM_downloader(lat, lon, dist)
    points = OSM.query_osm(amenity)

    print('number of {}: {}'.format(amenity, points))


if __name__ == '__main__':
    OSM_scraper()