import rasterio
import rasterio.mask
import numpy as np
import pandas as pd
import fiona

raster = "NGA_ppp_v2c_2020.tif"
shapefile = "nga_admbnda_adm1_osgof_20161215.shp"
destination = "test_G.csv"


def polygons_centroid(raster, shapefile, destination):
    """Calculates the weighted centroid of a list of polygons

    Args:
        raster: The raster file that countains the spatial weights (ex: Population raster)
        shapefile: The shapefile that countains the list of polygons.
        destination: The destination path for the resulting csv.

    Returns:
        A pandas DataFrame with the x, y coordinates of each polygon centroid.

    """
    x = []
    y = []
    id = []

    with rasterio.open(raster) as src:

        with fiona.open(shapefile, "r") as shapefile:

            for feature in shapefile:

                features = feature["geometry"]
                id.append(feature["id"])
                out_image, out_transform = rasterio.mask.mask(src, [features], crop=True)

                X_sum = out_image.sum(axis=1)[0, :]
                X_ind = np.arange(len(X_sum))
                i_centroid = int(np.average(X_ind, weights=X_sum))

                Y_sum = out_image.sum(axis=2)[0, :]
                Y_ind = np.arange(len(Y_sum))
                j_centroid = int(np.average(Y_ind, weights=Y_sum))

                x1, y1 = out_transform * (i_centroid, j_centroid)
                x.append(x1)
                y.append(y1)

                print(x1, y1)

    df = pd.DataFrame({"id": id, "x": x, "y": y})
    df.to_csv(destination)

    return df


polygons_centroid(raster, shapefile, destination)
