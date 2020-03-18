import arcpy
import os
from PNET_Functions import get_watershed_folders, delete_old, finish, delete_temps, is_empty, parse_bool

# -------------------------------------------------------------------------------
# Name:        PNET Step 3
# Purpose:     Prepares Points and Network For Reach Editing
# Author:      Tyler Hatch
#
# Created:     09/23/2019
# Latest Update: 1/22/2020
# -------------------------------------------------------------------------------


# The folder containing all watershed folders
root_folder = arcpy.GetParameterAsText(0)
# If True, this tool will only keep segmment min and segment max
restrict_segment_length = parse_bool(arcpy.GetParameterAsText(1))
# The minimum segment length to keep
min_seg = int(arcpy.GetParameterAsText(2))
# The maximum segment to keep
max_seg = int(arcpy.GetParameterAsText(3))
# If True, this indicates that the user edited the unsnapped points, and the corrections are now saved in
# ProjectWide/Intermediates/Points/Unsnapped_Fixed
fixed_points = parse_bool(arcpy.GetParameterAsText(4))


def main():

    # Initialize variables
    arcpy.env.overwriteOutput = True

    watershed_folders = get_watershed_folders(root_folder)

    delete_old(os.path.join(root_folder, "00_ProjectWide", "Intermediates", "Reach_Editing", "Inputs"))

    project_networks = []
    project_points = []
    temps_to_delete = []

    if fixed_points:
        network = os.path.join(root_folder, "00_ProjectWide", "Inputs", "Stream_Network", "Stream_Network.shp")
        fixed_folder = os.path.join(root_folder, "00_ProjectWide", "Intermediates", "Points", "Unsnapped_Fixed")
        save_fixed_points(network, fixed_folder, watershed_folders)

    # For each watershed:
    for watershed_folder in watershed_folders:

        arcpy.AddMessage("Starting {}...".format(watershed_folder))

        # Get all file names
        output_folder = os.path.join(watershed_folder, "Intermediates", "Reach_Editing", "Inputs")
        network = os.path.join(watershed_folder, "Inputs", "Stream_Network", "Stream_Network.shp")

        delete_old(output_folder)

        new_tor_filename = "temp_tor.shp"
        new_tor_points = os.path.join(watershed_folder, new_tor_filename)
        temps_to_delete.append(new_tor_points)

        new_bor_filename = "temp_bor.shp"
        new_bor_points = os.path.join(watershed_folder, new_bor_filename)
        temps_to_delete.append(new_bor_points)

        old_tor_points = os.path.join(watershed_folder, "Intermediates", "Points", "Snapped", "TOR_Points_Snapped.shp")
        old_bor_points = os.path.join(watershed_folder, "Intermediates", "Points", "Snapped", "BOR_Points_Snapped.shp")

        if fixed_points:
            # Merge the now fixed points with the snapped points, and use this going forward
            tor_temp_name = "temp_tor_merge.shp"
            tor_temp_merge = os.path.join(watershed_folder, tor_temp_name)
            tor_fixed = \
                os.path.join(watershed_folder, "Intermediates", "Points", "Unsnapped_Fixed", "TOR_Points_Fixed.shp")
            if not is_empty(tor_fixed):
                arcpy.Merge_management([tor_fixed, old_tor_points], tor_temp_merge)
                temps_to_delete.append(tor_temp_merge)
                old_tor_points = tor_temp_merge

            bor_temp_name = "temp_bor_merge.shp"
            bor_temp_merge = os.path.join(watershed_folder, bor_temp_name)
            bor_fixed = \
                os.path.join(watershed_folder, "Intermediates", "Points", "Unsnapped_Fixed", "BOR_Points_Fixed.shp")
            if not is_empty(bor_fixed):
                arcpy.Merge_management([bor_fixed, old_bor_points], bor_temp_merge)
                temps_to_delete.append(bor_temp_merge)
                old_bor_points = bor_temp_merge

        arcpy.CopyFeatures_management(old_tor_points, new_tor_points)
        arcpy.CopyFeatures_management(old_bor_points, new_bor_points)

        points_list = [new_tor_points, new_bor_points]
        tor_bor_list = ("\"TOR\"", "\"BOR\"")

        # This loops once for TOR points, once for BOR points
        for points, tor_bor in zip(points_list, tor_bor_list):

            # Add and populate TOR_BOR Field
            arcpy.AddField_management(points, "TOR_BOR", "TEXT")
            arcpy.CalculateField_management(points, "TOR_BOR", tor_bor)

        # Merge TOR_BOR Points
        merge_location = os.path.join(watershed_folder, "Intermediates",
                                      "Reach_Editing", "Inputs", "Points_Merge.shp")
        merge_edit_location = os.path.join(watershed_folder, "Intermediates",
                                           "Reach_Editing", "Outputs", "Points_Merge_To_Edit.shp")
        arcpy.Merge_management(points_list, merge_location)
        arcpy.Merge_management(points_list, merge_edit_location)
        project_points.append(merge_location)

        # Dissolve the network
        new_network = os.path.join(watershed_folder, "temp_network.shp")
        temps_to_delete.append(new_network)
        arcpy.Dissolve_management(network, new_network)

        network = new_network
        new_network = os.path.join(watershed_folder, "temp_network2.shp")
        temps_to_delete.append(new_network)

        # Split network at points
        arcpy.SplitLineAtPoint_management(network, merge_location, new_network, "10 METERS")
        network = new_network

        network_layer = "Network"
        arcpy.MakeFeatureLayer_management(network, network_layer)

        # Make a new layer of only segments that are between 80 and 400m, and intersect the field points
        if restrict_segment_length:
            arcpy.SelectLayerByAttribute_management\
                (network_layer, 'NEW_SELECTION', 'NHD_LEN >{} AND NHD_LEN <{}'.format(min_seg, max_seg))
            arcpy.SelectLayerByLocation_management\
                (network_layer, 'INTERSECT', merge_location, selection_type="SUBSET_SELECTION")
        else:
            arcpy.SelectLayerByLocation_management\
                (network_layer, 'INTERSECT', merge_location)

        save_location = os.path.join(watershed_folder, "Intermediates",
                                     "Reach_Editing", "Inputs", "Stream_Network_Segments.shp")
        edit_location = os.path.join(watershed_folder, "Intermediates",
                                     "Reach_Editing", "Outputs", "Stream_Network_Segments_To_Edit.shp")
        arcpy.CopyFeatures_management(network_layer, save_location)
        arcpy.CopyFeatures_management(network_layer, edit_location)
        project_networks.append(save_location)

    arcpy.AddMessage("Saving ProjectWide...")
    make_projectwide(root_folder, project_points, project_networks)

    delete_temps(temps_to_delete)
    finish()


def save_fixed_points(stream_network, fixed_folder, watershed_folders):

    arcpy.AddMessage("\nSaving Fixed Points...\n")

    # Catches error on script rerun
    if os.path.exists(os.path.join(fixed_folder, "TOR_Points_Fixed.shp")):
        arcpy.Rename_management(os.path.join(fixed_folder, "TOR_Points_Fixed.shp"), "To_Fix_TOR.shp")
    if os.path.exists(os.path.join(fixed_folder, "BOR_Points_Fixed.shp")):
        arcpy.Rename_management(os.path.join(fixed_folder, "BOR_Points_Fixed.shp"), "To_Fix_BOR.shp")

    # Get shapefile with points
    tor_points = os.path.join(fixed_folder, "To_Fix_TOR.shp")
    bor_points = os.path.join(fixed_folder, "To_Fix_BOR.shp")

    # 10m Snap to network (in case editing wasn't perfect
    arcpy.Snap_edit(tor_points, [[stream_network, "EDGE", "10 Meters"]])
    arcpy.Snap_edit(bor_points, [[stream_network, "EDGE", "10 Meters"]])

    # For each watershed
    for watershed_folder in watershed_folders:
        # Get the boundary
        boundary = os.path.join(watershed_folder, "Inputs", "Watershed_Boundary", "Watershed_Boundary.shp")

        # Get the save loc for tor and bor
        tor_save = os.path.join(watershed_folder, "Intermediates", "Points", "Unsnapped_Fixed", "TOR_Points_Fixed.shp")
        bor_save = os.path.join(watershed_folder, "Intermediates", "Points", "Unsnapped_Fixed", "BOR_Points_Fixed.shp")

        # Clip the points to that boundary
        arcpy.Clip_analysis(tor_points, boundary, tor_save)
        arcpy.Clip_analysis(bor_points, boundary, bor_save)

    # Rename fixed project wide
    arcpy.Rename_management(tor_points, "TOR_Points_Fixed.shp")
    arcpy.Rename_management(bor_points, "BOR_Points_Fixed.shp")


def make_projectwide(root_folder, points, networks):
    save_folder = os.path.join(root_folder, "00_ProjectWide", "Intermediates", "Reach_Editing", "Inputs")
    to_edit_folder = os.path.join(root_folder, "00_ProjectWide", "Intermediates", "Reach_Editing", "Outputs")

    arcpy.Merge_management(networks, os.path.join(save_folder, "Stream_Network_Segments.shp"))
    arcpy.Merge_management(points, os.path.join(save_folder, "Points_Merge.shp"))
    arcpy.Merge_management(networks, os.path.join(to_edit_folder, "Stream_Network_Segments_To_Edit.shp"))
    arcpy.Merge_management(points, os.path.join(to_edit_folder, "Points_Merge_To_Edit.shp"))


if __name__ == "__main__":
    main()
