import arcpy
import os
from PNET_Functions import is_even, get_watershed_folders, delete_old, finish, parse_bool

# -------------------------------------------------------------------------------
# Name:        PNET Step 2
# Purpose:     Snaps all points to the stream network
# Author:      Tyler Hatch
#
# Created:     09/23/2019
# Latest Update: 5/4/2020
# -------------------------------------------------------------------------------

# A list of file locations pointing to each watershed's All_points folder
root_folder = arcpy.GetParameterAsText(0)
# Set this to true if you want the threshold value to be used. This should almost always be True
use_threshold = parse_bool(arcpy.GetParameterAsText(1))
# The longest distance (m) to go before snapping stops and remaining points are considered outliers to be investigated
threshold_range = int(arcpy.GetParameterAsText(2))
# Snapping distances will increase by this increment (m). Default is ten. Lower values mean longer run time.
custom_increment = 10


def main():

    # Initialize Variables
    arcpy.env.overwriteOutput = True
    saved_tor_points_snapped = []
    saved_bor_points_snapped = []
    saved_tor_points_unsnapped = []
    saved_bor_points_unsnapped = []

    watershed_folders = get_watershed_folders(root_folder)

    # Delete old content from this tool being re run.
    delete_old(os.path.join(root_folder, "00_ProjectWide", "Intermediates", "Points", "Snapped"))
    delete_old(os.path.join(root_folder, "00_ProjectWide", "Intermediates", "Points", "Unsnapped"))

    # This loops for every watershed
    for watershed_folder in watershed_folders:

        arcpy.AddMessage("Starting {}...".format(watershed_folder))

        # Get all file names
        output_folder = os.path.join(watershed_folder, "Intermediates", "Points")
        network = os.path.join(watershed_folder, "Inputs", "Stream_Network", "Stream_Network.shp")

        delete_old(os.path.join(output_folder, "Snapped"))
        delete_old(os.path.join(output_folder, "Unsnapped"))

        bor_points_old = os.path.join(watershed_folder, "Inputs", "Points", "BOR_Points.shp")
        tor_points_old = os.path.join(watershed_folder, "Inputs", "Points", "TOR_Points.shp")

        bor_points_new_temp = os.path.join(output_folder, "BOR_Points_Temp.shp")
        tor_points_new_temp = os.path.join(output_folder, "TOR_Points_Temp.shp")

        bor_points_new_snapped = os.path.join(output_folder, "Snapped", "BOR_Points_Snapped.shp")
        tor_points_new_snapped = os.path.join(output_folder, "Snapped", "TOR_Points_Snapped.shp")
        saved_bor_points_snapped.append(bor_points_new_snapped)
        saved_tor_points_snapped.append(tor_points_new_snapped)

        bor_points_new_unsnapped = os.path.join(output_folder, "Unsnapped", "BOR_Points_Unsnapped.shp")
        tor_points_new_unsnapped = os.path.join(output_folder, "Unsnapped", "TOR_Points_Unsnapped.shp")
        saved_bor_points_unsnapped.append(bor_points_new_unsnapped)
        saved_tor_points_unsnapped.append(tor_points_new_unsnapped)

        arcpy.CopyFeatures_management(bor_points_old, bor_points_new_temp)
        arcpy.CopyFeatures_management(tor_points_old, tor_points_new_temp)

        points_list = [tor_points_new_temp, bor_points_new_temp]

        # This loops once for TOR and once for BOR, snaps all points
        for counter, points in enumerate(points_list):
            if counter == 0:
                label = "TOR"
            else:
                label = "BOR"
            snap_dist = 0
            all_snapped = False
            total_points = arcpy.GetCount_management(points)
            base_list = []

            # TODO make more general
            for row in arcpy.da.SearchCursor(points, "RchID"):
                base_list.append(row[0])
            snap_value_list = [999] * len(base_list)
            arcpy.AddField_management(points, "SnapDist", "SHORT")

            # This loops until all points are snapped to the network, incrementing the snap distance by 10 each time.
            while all_snapped is False:

                # Increment snap distance by an increment
                snap_dist += custom_increment
                snap_name = str(snap_dist) + " Meters"
                arcpy.AddMessage("\t Snapping {} {}".format(label, snap_name))

                # Snap the points
                arcpy.Snap_edit(points, [[network, "EDGE", snap_name]])
                temp = os.path.join(watershed_folder, "temporary.shp")

                # Create an intersect of the points and the network
                arcpy.Intersect_analysis([points, network], temp)
                current_snapped = arcpy.GetCount_management(temp)

                # Update each snap distance value for points that were just snapped
                # TODO make more general
                for row in arcpy.da.SearchCursor(temp, "RchID"):
                    if snap_value_list[base_list.index(row[0])] == 999:
                        snap_value_list[base_list.index(row[0])] = snap_dist

                # Checks to see if every point has been snapped yet
                if (str(current_snapped) == str(total_points)) or \
                        (use_threshold is True and snap_dist >= threshold_range):

                    # All points have been snapped, or are beyond the given threshold
                    all_snapped = True

                    # Delete temporary file
                    arcpy.Delete_management(temp)

            # Add XY data to each point
            arcpy.AddXY_management(points)

            # Populate the snap distance field
            with arcpy.da.UpdateCursor(points, "SnapDist") as cursor:
                for count, row in enumerate(cursor):
                    row[0] = snap_value_list[count]
                    cursor.updateRow(row)

            # Create a layer to select from
            points_layer = "Points"
            arcpy.MakeFeatureLayer_management(points, points_layer)

            # Save snapped and unsnapped points
            if label == "TOR":
                arcpy.SelectLayerByAttribute_management(points_layer, 'NEW_SELECTION', 'SnapDist >= 999')
                arcpy.CopyFeatures_management(points_layer, tor_points_new_unsnapped)
                arcpy.SelectLayerByAttribute_management(points_layer, 'SWITCH_SELECTION')
                arcpy.CopyFeatures_management(points_layer, tor_points_new_snapped)
                arcpy.SelectLayerByAttribute_management(points_layer, 'CLEAR_SELECTION')

            if label == "BOR":
                arcpy.SelectLayerByAttribute_management(points_layer, 'NEW_SELECTION', 'SnapDist >= 999')
                arcpy.CopyFeatures_management(points_layer, bor_points_new_unsnapped)
                arcpy.SelectLayerByAttribute_management(points_layer, 'SWITCH_SELECTION')
                arcpy.CopyFeatures_management(points_layer, bor_points_new_snapped)
                arcpy.SelectLayerByAttribute_management(points_layer, 'CLEAR_SELECTION')

        # Delete temporary files
        arcpy.Delete_management(bor_points_new_temp)
        arcpy.Delete_management(tor_points_new_temp)

    arcpy.AddMessage("Saving ProjectWide Files...")

    output_folder = os.path.join(root_folder, "00_ProjectWide", "Intermediates", "Points")

    bor_points_new_snapped = os.path.join(output_folder, "Snapped", "BOR_Points_Snapped.shp")
    tor_points_new_snapped = os.path.join(output_folder, "Snapped", "TOR_Points_Snapped.shp")
    bor_points_new_unsnapped = os.path.join(output_folder, "Unsnapped", "BOR_Points_Unsnapped.shp")
    tor_points_new_unsnapped = os.path.join(output_folder, "Unsnapped", "TOR_Points_Unsnapped.shp")

    arcpy.Merge_management(saved_bor_points_snapped, bor_points_new_snapped)
    arcpy.Merge_management(saved_tor_points_snapped, tor_points_new_snapped)
    arcpy.Merge_management(saved_bor_points_unsnapped, bor_points_new_unsnapped)
    arcpy.Merge_management(saved_tor_points_unsnapped, tor_points_new_unsnapped)

    arcpy.Copy_management(bor_points_new_unsnapped, os.path.join(output_folder, "Unsnapped_Fixed", "To_Fix_BOR.shp"))
    arcpy.Copy_management(tor_points_new_unsnapped, os.path.join(output_folder, "Unsnapped_Fixed", "To_Fix_TOR.shp"))

    finish()


if __name__ == "__main__":
    main()
