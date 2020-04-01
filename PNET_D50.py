import arcpy
import os
import shutil
from PNET_Functions import get_watershed_folders, delete_old, create_csv, get_fields, csv_to_list, parse_multistring
import scipy.stats as stat
import numpy as np
import matplotlib.pyplot as plt

# -------------------------------------------------------------------------------
# Name:        PNET D50
# Purpose:     Adds a D50 field from data put into PNET
#
# Author:      Tyler Hatch
#
# Created:     3/1/2020
# Latest Update: 3/1/2020
# -------------------------------------------------------------------------------

# The folder containing all watershed folders
root_folder = arcpy.GetParameterAsText(0)

discharge_field = "iHyd_Q2"
bankfull_field = "BFWIDTH"
slope_field = "iGeo_Slope"
input_fields = [discharge_field, bankfull_field, slope_field]


def main():
    # Initialize variables and file locations
    arcpy.env.overwriteOutput = True
    watershed_folders = get_watershed_folders(root_folder)

    # Setup projectwide data
    data_path = r"Outputs/Extracted_Data/Extraction_Merge_Points.shp"
    watershed_folders.append(os.path.join(root_folder, "00_ProjectWide"))

    for watershed in watershed_folders:

        # get filepath
        arcpy.AddMessage("Working on {}...".format(watershed))
        watershed_extracted = os.path.join(watershed, data_path)

        # Check to make sure we have the necessary fields
        existing_fields = get_fields(watershed_extracted)
        can_run = True
        for input_field in input_fields:
            if input_field not in existing_fields:
                can_run = False
                arcpy.AddWarning("Fields needed to calculate D50 not found, no D50 will be calculated")

        # Calculate and add D50 for each point
        if can_run:

            # Add the fields where we will store d50 values
            d50_fields = ["PredD50_03", "PredD50_04"]
            arcpy.AddField_management(watershed_extracted, d50_fields[0], "FLOAT")
            arcpy.AddField_management(watershed_extracted, d50_fields[1], "FLOAT")

            # Add d50 values to every point
            with arcpy.da.UpdateCursor(watershed_extracted, input_fields + d50_fields) as cursor:
                for row in cursor:
                    # Calculate d50 with given values
                    d50_03, d50_04 = calculate_d50(row[0], row[1], row[2])
                    # Update with new d50 values
                    cursor.updateRow([row[0], row[1], row[2], d50_03, d50_04])

            # Update CSV
            create_csv(os.path.join(watershed, "Outputs", "Extracted_Data", "All_Data.csv"), watershed_extracted)


def calculate_d50(discharge, bankfull, slope, n=.035, tc03=.03, tc04=.04):

    # Calculate using TC03
    tco3_d50 = ((997 * 9.81) * n * ((discharge-.0283168) ** (3/5)) * (bankfull ** (-3/5)) * (slope ** (7/10))) / \
               ((2650-997) * 9.81 * tc03)

    # Calculate using TC04
    tco4_d50 = ((997 * 9.81) * n * ((discharge-.0283168) ** (3/5)) * (bankfull ** (-3/5)) * (slope ** (7/10))) / \
               ((2650-997) * 9.81 * tc04)

    return tco3_d50, tco4_d50


if __name__ == "__main__":
    main()
