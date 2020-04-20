import arcpy
import os
import shutil
from PNET_Functions import get_watershed_folders, delete_old, create_csv, \
    get_fields, csv_to_list, parse_multistring, make_folder
import scipy.stats as stat
import numpy as np
import matplotlib.pyplot as plt
import math

# -------------------------------------------------------------------------------
# Name:        PNET Step 10
# Purpose:     Creates Comparison Graphs for categorical data
#
# Author:      Tyler Hatch
#
# Created:     3/1/2020
# Latest Update: 3/1/2020
# -------------------------------------------------------------------------------

# The projectwide all_data shapefile
all_data_shapefile = r'C:\Users\Tyler\Desktop\Work\Test_Run\00_ProjectWide\Outputs\Comparisons\Numerical\Numerical_Comparison_Points.shp'
# Outliers CSV
outliers_csv = r'C:\Users\Tyler\Desktop\Work\Test_Run\00_Scripttesting\Outliers.csv'


def main():

    # Initialize variables and file locations
    arcpy.env.overwriteOutput = True

    fields, outliers = read_outliers_csv(outliers_csv)

    for field, outlier_reach in zip(fields, outliers):
        with arcpy.da.UpdateCursor(all_data_shapefile, ["RchID", field]) as cursor:
            for row in cursor:
                # If the current reach ID is in the list of outlier reaches
                if row[0] in outlier_reach:
                    row[1] = 0.0
                cursor.updateRow(row)


def read_outliers_csv(to_read):

    to_read_list = csv_to_list(to_read)
    fields = []
    outliers = []
    curr_outliers = []

    for row in to_read_list:

        # This represents a new field
        if len(row) == 1:
            fields.append(row[0])
            outliers.append(curr_outliers)
            curr_outliers = []

        # We are reading in outliers
        else:
            # Use row[1] to skip over id field
            curr_outliers.append(row[1])

    # Remove blank first entry
    outliers.pop(0)

    # Add in final outliers
    outliers.append(curr_outliers)


    return fields, outliers




if __name__ == "__main__":
    main()
