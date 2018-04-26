
def aggregate(input_rst, output_rst, scale):
    """
    Downsample (upscale) a raster by a given factor and replace no_data value with 0.
    Args:
        input_rst: path to the input raster in a format supported by georaster
        output_rst: path to the scaled output raster in a format supported by georaster
        scale: The scale (integer) by which the raster in upsampeld.
    Returns:
        Save the output raster to disk.
    """
    import georasters as gr
    input_gr = gr.from_file(input_rst)

    # No data values are replaced with 0 to prevent summing them in each block.
    input_gr.raster.data[input_gr.raster.data == input_gr.nodata_value] = 0
    input_gr.nodata_value = 0

    output_gr = input_gr.aggregate(block_size=(scale, scale))

    output_gr.to_tiff(output_rst.replace(".tif", ""))


def replace_nodata(input_rst, output_rst, value):
    """
    Replace the no_data value of a raster in both the data and the metadata of a raster.
    Args:
        input_rst: path to the input raster in a format supported by rasterio
        output_rst: path to the output raster in a format supported by rasterio
        value: The new no_data value.
    Returns:
        Save the output raster to disk.
    """
    import rasterio
    with rasterio.open(input_rst, 'r') as src:
        data = src.read()
        data[data == src.nodata] = value
        profile = src.profile
    with rasterio.open(output_rst, 'w', **profile) as dst:
        dst.nodata = value
        dst.write(data)


def reproject(input_rst, output_rst, reference_rst):
    """
    Reproject a raster to the coordinates system of another raster and re-samples the data using Nearest Neighbor interpolation.
    Args:
        input_rst: path to the input raster in a format supported by gdal
        output_rst: path to the output raster in a format supported by gdal
        reference_rst: path to the reference raster in a format supported by gdal
    Returns:
        Save the output raster to disk.
    """
    from osgeo import gdal, gdalconst
    src = gdal.Open(input_rst, gdalconst.GA_ReadOnly)
    src_proj = src.GetProjection()

    match_ds = gdal.Open(reference_rst, gdalconst.GA_ReadOnly)
    match_proj = match_ds.GetProjection()
    match_geotrans = match_ds.GetGeoTransform()
    wide = match_ds.RasterXSize
    high = match_ds.RasterYSize

    dst = gdal.GetDriverByName('GTiff').Create(output_rst, wide, high, 1, gdalconst.GDT_Float32)
    dst.SetGeoTransform(match_geotrans)
    dst.SetProjection(match_proj)
    band = dst.GetRasterBand(1)
    band.SetNoDataValue(0.0)

    gdal.ReprojectImage(src, dst, src_proj, match_proj, gdalconst.GRA_NearestNeighbour)

    del dst


def multiply(input_rst1, input_rst2, output_rst):
    """
    Multiply two rasters cell by cell.
    Args:
        input_rst1: path to the input raster in a format supported by gdal
        input_rst2: path to the output raster in a format supported by gdal
        output_rst: path to the raster to copy the referenced system (projection and transformation) from
    Returns:
        Save the output raster to disk.
    """
    import rasterio

    with rasterio.open(input_rst1) as src1:
        with rasterio.open(input_rst2) as src2:
            data1 = src1.read()
            data2 = src2.read()
            data1[data1 == src1.nodata] = 0
            data2[data2 == src2.nodata] = 0
            final = data1 * data2
            profile = src1.profile

    with rasterio.open(output_rst, 'w', **profile) as dst:
        dst.nodata = 0
        dst.write(final)


def weighted_sum_by_polygon(input_shp, input_rst, weight_rst, output_shp):
    """
    Take the weighted sum of two rasters (indicator and weights) within each polygon of a shapefile.

    input_rst and weight_rst need to be in the same projection system and have the same shape

    Args:
        input_shp: path to the input shapefile in a format support by geopandas
        input_rst: path to the raster containing the value you want to aggregate
        weight_rst: path to the raster containing the weights (ex: population data)
        output_shp: path to the input shapefile in a format support by geopandas
    Returns:
        Save a copy of the shapefile to disk with the resulting weighted sum as a new attribute of each polygon.
    """
    import geopandas as gpd
    import rasterio
    import rasterio.mask
    import json
    import numpy as np

    mult_rst = input_rst.replace(".tif", "_multiplied.tif")
    multiply(input_rst, weight_rst, mult_rst)

    X = []
    Y = []
    gdf = gpd.read_file(input_shp)
    gdf['indicator'] = None

    with rasterio.open(mult_rst) as src1:
        with rasterio.open(weight_rst) as src2:
            index = 0
            gdf = gdf.to_crs(crs=src1.crs.data)  # Re-project shape-file according to mult_rst
            features = json.loads(gdf.to_json())['features']
            for feature in features:
                geom = feature['geometry']
                out_image, out_transform = rasterio.mask.mask(src1, [geom], crop=True)
                out_image2, out_transform2 = rasterio.mask.mask(src2, [geom], crop=True)
                out_image[out_image == src1.nodata] = 0
                out_image2[out_image2 == src2.nodata] = 0
                x = out_image.sum() / out_image2.sum()
                y = out_image2.sum()
                X.append(x)
                Y.append(y)
                print(gdf.loc[index, 'admin1Name'], x, y)
                gdf.loc[index, 'FCS'] = round(x, 2)
                gdf.loc[index, 'population'] = int(y)
                index += 1

    print("Total_Weights : {}".format(np.array(Y).sum()))
    gdf.to_file(output_shp)


# Inputs
hrm_raster = 'inputs/88.tif'
pop_raster = 'inputs/SEN_pph_v2b_2015_UNadj.tif'
senegal_shp = "inputs/sen_admbnda_adm1_1m_gov_ocha_04082017.shp"
senegal_adm3_shp = "inputs/sen_admbnda_adm3_1m_gov_ocha_04082017.shp"


# Outputs
hrm_raster_repr = 'intermediary/88_agg.tif'
pop_raster_agg = 'intermediary/SEN_pph_v2b_2015_UNadj_repr.tif'
pop_raster_nodata = 'intermediary/SEN_pph_v2b_2015_UNadj_repr_nodata.tif'
senegal_adm3_shp_FCS = "results/sen_admbnda_adm3_1m_gov_ocha_04082017_FCS.shp"

# Script 1 : Aggregate WorldPop to 1km cell size
aggregate(pop_raster, pop_raster_agg, 10)
reproject(hrm_raster, hrm_raster_repr, pop_raster_agg)
weighted_sum_by_polygon(senegal_adm3_shp, hrm_raster_repr, pop_raster_agg, senegal_adm3_shp_FCS)

# Script 2 : Leave WorldPop at 100m cell size and resample input raster to match WorldPop (slower but more accurate)
reproject(hrm_raster, hrm_raster_repr, pop_raster)
weighted_sum_by_polygon(senegal_adm3_shp, hrm_raster_repr, pop_raster, senegal_adm3_shp_FCS)
