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

# The folder containing all watershed folders
root_folder = arcpy.GetParameterAsText(0)


def main():

    outliers_csv = os.path.join(root_folder, "00_Projectwide", "Outputs", "Comparisons", "Numerical", "Outliers.csv")

    if not os.path.isfile(outliers_csv):
        arcpy.AddMessage("Please run the Outliers R script before this script")

    # Initialize variables and file locations
    arcpy.env.overwriteOutput = True
    watershed_folders = get_watershed_folders(root_folder)
    watershed_folders.append(os.path.join(root_folder, "00_Projectwide"))
    fields, outliers = read_outliers_csv(outliers_csv)

    for watershed in watershed_folders:

        arcpy.AddMessage("Working on {}...".format(watershed))

        output_location = os.path.join(watershed, "Outputs", "Comparisons", "Numerical")
        shapefile_in = os.path.join(output_location, "Numerical_Comparison_Points.shp")
        shapefile_out = os.path.join(output_location, "Numerical_Comparison_Points_Outliers_Removed.shp")
        arcpy.Copy_management(shapefile_in, shapefile_out)
        csv = os.path.join(output_location, "Numerical_Comparison_Data_Outliers_Removed.csv")
        for field, outlier_reach in zip(fields, outliers):
            if field in get_fields(shapefile_out):
                arcpy.AddMessage("\tFixing Field {}...".format(field))
                with arcpy.da.UpdateCursor(shapefile_out, ["RchID", field]) as cursor:
                    for row in cursor:
                        # If the current reach ID is in the list of outlier reaches
                        if row[0] in outlier_reach:
                            row[1] = -999
                        cursor.updateRow(row)

        create_csv(csv, shapefile_out)







if __name__ == "__main__":
    main()
