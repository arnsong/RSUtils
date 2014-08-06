import sys
import os
import re

import gdal
from gdalconst import *

from osgeo import ogr
from osgeo import osr

import numpy as np

from Tkinter import Tk
from tkFileDialog import askdirectory



"""
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import numpy as np
"""

def GDALInfoReportCorner( hDataset, hTransform, corner_name, x, y ):


    line = "%-11s " % corner_name

    #/* -------------------------------------------------------------------- */
    #/*      Transform the point into georeferenced coordinates.             */
    #/* -------------------------------------------------------------------- */
    adfGeoTransform = hDataset.GetGeoTransform(can_return_null = True)
    if adfGeoTransform is not None:
        dfGeoX = adfGeoTransform[0] + adfGeoTransform[1] * x \
          + adfGeoTransform[2] * y
        dfGeoY = adfGeoTransform[3] + adfGeoTransform[4] * x \
          + adfGeoTransform[5] * y
          
    else:
        line = line + ("(%7.1f,%7.1f)" % (x, y ))
        print(line)
        return False
    
    #/* -------------------------------------------------------------------- */
    #/*      Report the georeferenced coordinates.                           */
    #/* -------------------------------------------------------------------- */
    if abs(dfGeoX) < 181 and abs(dfGeoY) < 91:
        line = line + ( "(%12.7f,%12.7f) " % (dfGeoX, dfGeoY ))

    else:
        line = line + ( "(%12.3f,%12.3f) " % (dfGeoX, dfGeoY ))
        
    #/* -------------------------------------------------------------------- */
    #/*      Transform to latlong and report.                                */
    #/* -------------------------------------------------------------------- */
    if hTransform is not None:
        pnt = hTransform.TransformPoint(dfGeoX, dfGeoY, 0)
        if pnt is not None:
            line = line + ( "(%s," % gdal.DecToDMS( pnt[0], "Long", 2 ) )
            line = line + ( "%s)" % gdal.DecToDMS( pnt[1], "Lat", 2 ) )
            
    print(line)
            
    return pnt[0], pnt[1]           

def read_batch():
    
    f = open( 'test.kml', 'w' )
    
    """
    Write kml file header
    """
    f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
    f.write('\t <kml xmlns="http://www.opengis.net/kml/2.2">\n')
    f.write('\t\t <Document>\n')
    
    """
    Specify line color style
    """
    f.write( '<Style id="yellowLineGreenPoly">\n')
    f.write( '<LineStyle>\n' )
    f.write( '<color>7f00ffff</color>\n' )
    f.write( '<width>2</width>\n' )
    f.write( '</LineStyle>\n' )
    f.write( '</Style>\n' )
    
    
    # Open user dialog box to get file
    Tk().withdraw()
    dirname = askdirectory()
    
    if not dirname:
        print "No directory selected. Exiting."
        read_flag = 0
    else:
        print(dirname)
        
    for fname in os.listdir(dirname):
        if fname.endswith('.tif') or fname.endswith('.img'):
            # Split path + filename from file extension
            filePath, fileExtension = os.path.splitext(fname)
            filename = dirname + '/' + fname
            
            # Open file
            img = gdal.Open( filename, GA_ReadOnly )
            print "Image read: " + fname
            
            searchObj = re.search( "[0-9]{8}", filePath )
            timeString = searchObj.group(0)
            timeStamp = timeString[0:4] + '-' + timeString[4:6] + '-' + timeString[6:8]
            
            print "Image date: " + timeStamp + "\n"
            
            # Get projection information
            geotransform = img.GetGeoTransform()
            originX = geotransform[0]             
            originY = geotransform[3]
            
            pixelWidth = geotransform[1]
            pixelHeight = geotransform[5]
            
            rotation1 = geotransform[2]
            rotation2 = geotransform[4]
            
            cols = img.RasterXSize
            rows = img.RasterYSize
            bands = img.RasterCount

            # Print raster info to screen
            print "File extension: " + fileExtension
            print "Origin X: " + repr(originX) + " Y: " + repr(originY)
            print "Rotation: Angle 1: " + repr(rotation1) + " Angle 2: " + repr(rotation2)
            print "Pixel width: " + repr(pixelWidth) + " height: " + repr(pixelHeight)
            print "Columns: " + repr(cols) + " Rows: " + repr(rows) + " Bands: " + repr(bands)
        
        
            """
            ERDAS Imagine file
            """
            if fileExtension == '.img':
                lat = np.zeros((5,))
                lon = np.zeros((5,))
                
                # Calculate affine coordinates of lower right corner
                x_max = originX + pixelWidth * cols  + geotransform[2] * rows + pixelWidth / 2.0
                y_max = originY + geotransform[4] * cols + pixelHeight * rows + pixelHeight / 2.0
                
                # Extract projection information
                srs = osr.SpatialReference()
                srs.ImportFromWkt(img.GetProjectionRef())
                
                # Create transform projection
                srsLatLong = osr.SpatialReference()
                srsLatLong = srs.CloneGeogCS()
                
                # Create transform object
                ct = osr.CoordinateTransformation(srs,srsLatLong)
                
                print( "Corner Coordinates:" )
                
                """
                Extract scene corner coordinates from header metadata
                """
                ( lon[0], lat[0] ) = GDALInfoReportCorner( img, ct, "Upper Left", \
                                                           0.0, 0.0 )
                ( lon[1], lat[1] ) = GDALInfoReportCorner( img, ct, "Upper Right", \
                                                           img.RasterXSize, 0.0 )
                ( lon[2], lat[2] ) = GDALInfoReportCorner( img, ct, "Lower Right", \
                                                           img.RasterXSize, \
                                                           img.RasterYSize )
                ( lon[3], lat[3] ) = GDALInfoReportCorner( img, ct, "Lower Left", \
                                                           0.0, img.RasterYSize)
                ( lon[4], lat[4] ) = GDALInfoReportCorner( img, ct, "Upper Left", \
                                                           0.0, 0.0 )
                print "\n\n"
            
                """
                Create polygon
                """
                poly = ogr.Geometry(ogr.wkbLineString)
                
                for i in range(lon.shape[0]):
                    poly.AddPoint(lon[i],lat[i])
                    
            elif fileExtension == '.tif':
                # Get control points
                controlPoints = img.GetGCPs()
                
                # Initialize lat/long coordinate variables
                lon = np.zeros(len(controlPoints))
                lat = np.zeros(len(controlPoints))
                
                for i in range(len(controlPoints)):
                    lon[i] = controlPoints[i].GCPX
                    lat[i] = controlPoints[i].GCPY
                                
                """
                Create polygon
                """
                poly = ogr.Geometry(ogr.wkbLineString)
                poly.AddPoint(lon.min(), lat.max())
                poly.AddPoint(lon.max(), lat.max())
                poly.AddPoint(lon.max(), lat.min())
                poly.AddPoint(lon.min(), lat.min())
                poly.AddPoint(lon.min(), lat.max())
            
            
            kml = poly.ExportToKML()
        
            """
            Write geometry to file
            """
            f.write('\t\t\t <Placemark>\n')
            f.write('<name>' + fname + '</name>')
            f.write('<styleUrl>#yellowLineGreenPoly</styleUrl>\n' )
            f.write('<TimeStamp>\n <when>\n' + timeStamp + '</when>\n</TimeStamp>\n' )
            f.write(kml)
            f.write('\t\t\t</Placemark>\n')
            """
            f.write('<GroundOverlay id="' + fname + '">')
            f.write('<name>' + fname + '</name>')
            f.write('<styleUrl>#yellowLineGreenPoly</styleUrl>\n' )
            f.write('<color>501400FF</color>')
            f.write('<altitude>0</altitude>')
            f.write('<TimeStamp>\n <when>\n' + timeStamp + '</when>\n</TimeStamp>\n' )
            f.write('<gx:LatLonQuad>')
            for i in range(lon.shape[0]):
                f.write( repr(lon[i]) + ',' + repr(lat[i]) + ' ')
            f.write('</gx:LatLonQuad>')
            f.write('</GroundOverlay>')
            """
                
    """
    Write close out tags
    """
    
    f.write('\t\t</Document>\n')
    f.write('\t</kml>\n')
    
    f.close()
