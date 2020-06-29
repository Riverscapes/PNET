import arcpy
import os
from collections import Counter
import PNET_Functions
import shutil
import scipy.stats as stat
import numpy as np
import matplotlib.pyplot as plt
import math

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
# If True, this indicates that the user edited the unsnapped points, and the corrections are now saved in
# ProjectWide/Intermediates/Points/Unsnapped_Fixed
fixed_points = PNET_Functions.parse_bool(arcpy.GetParameterAsText(1))
# A list of links to shapefiles that contain entire model runs
data_networks_list_in = PNET_Functions.parse_multistring(arcpy.GetParameterAsText(2))
# All segments below this length in meters will not be considered when calculating multi segment reaches.
length_cutoff = int(arcpy.GetParameterAsText(3))
# This determines if D50 is calculated or not.
perform_d50 = PNET_Functions.parse_bool(arcpy.GetParameterAsText(4))
# The database containing all field data
field_db = arcpy.GetParameterAsText(5)
# CSV to set numerical field data from instead (optional, expects headers)
input_field_csv = arcpy.GetParameterAsText(6)
# CSV to set comparison field data from instead (expects headers)
input_comparison_field_csv = arcpy.GetParameterAsText(7)


def main():

    # Old Step 3
    reach_preparation(root_folder, fixed_points)
    # Old Step 4
    reach_editing(root_folder)
    # Old Step 5
    data_cleaning(root_folder)
    # Old Step 6
    data_network_input(root_folder, data_networks_list_in)
    # Old Step 7
    data_network_extraction(root_folder, length_cutoff)
    # Old Step 8a
    reach_merging(root_folder)
    # Old Step 8b
    calculate_d50(root_folder)
    # Old Step 9a
    numerical_comparisons(root_folder, field_db, input_field_csv)


def reach_preparation(root_folder, fixed_points):
    # Initialize variables
    arcpy.env.overwriteOutput = True

    watershed_folders = PNET_Functions.get_watershed_folders(root_folder)

    PNET_Functions.delete_old(os.path.join(root_folder, "00_ProjectWide", "Intermediates", "Reach_Editing", "Inputs"))

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

        PNET_Functions.delete_old(output_folder)

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
            if not PNET_Functions.is_empty(tor_fixed):
                arcpy.Merge_management([tor_fixed, old_tor_points], tor_temp_merge)
                temps_to_delete.append(tor_temp_merge)
                old_tor_points = tor_temp_merge

            bor_temp_name = "temp_bor_merge.shp"
            bor_temp_merge = os.path.join(watershed_folder, bor_temp_name)
            bor_fixed = \
                os.path.join(watershed_folder, "Intermediates", "Points", "Unsnapped_Fixed", "BOR_Points_Fixed.shp")
            if not PNET_Functions.is_empty(bor_fixed):
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

        # Make a new layer of only segments that intersect the field points
        arcpy.SelectLayerByLocation_management \
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

    PNET_Functions.delete_temps(temps_to_delete)
    PNET_Functions.finish()


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


def reach_editing(root_folder):

    # Initialize variables
    arcpy.env.overwriteOutput = True

    watershed_folders = PNET_Functions.get_watershed_folders(root_folder)
    PNET_Functions.delete_old(os.path.join(root_folder, "00_ProjectWide", "Intermediates", "Reach_Editing", "Outputs"))
    temps_to_delete = []
    to_merge_points = []
    to_merge_reaches = []

    for watershed in watershed_folders:
        arcpy.AddMessage("Starting {}...".format(watershed))

        # Get file names
        input_folder = os.path.join(watershed, "Intermediates", "Reach_Editing", "Inputs")
        output_folder = os.path.join(watershed, "Intermediates", "Reach_Editing", "Outputs")
        PNET_Functions.delete_old(output_folder)

        stream_seg = os.path.join(input_folder, "Stream_Network_Segments.shp")
        points = os.path.join(input_folder, "Points_Merge.shp")

        stream_seg_copy = os.path.join(input_folder, "Stream_Network_Segments_To_Edit_Temp.shp")
        points_copy = os.path.join(input_folder, "Points_Merge_To_Edit_Temp.shp")

        temps_to_delete.append(stream_seg_copy)
        temps_to_delete.append(points_copy)

        arcpy.Copy_management(stream_seg, stream_seg_copy)
        arcpy.Copy_management(points, points_copy)

        stream_seg = stream_seg_copy
        points = points_copy

        # Spatial jon stream network segments by points

        fields_to_remove = ["TARGET_FID", "JOIN_FID", "Join_Count"]

        spatial_joined = os.path.join(input_folder, "Spatial_Joined_Temp.shp")
        temps_to_delete.append(spatial_joined)
        PNET_Functions.remove_fields(fields_to_remove, stream_seg)
        arcpy.SpatialJoin_analysis(stream_seg, points, spatial_joined, "JOIN_ONE_TO_MANY")

        # Get an attribute table list of the joined shapefile to analyze
        stream_seg_list = PNET_Functions.attribute_table_to_list(spatial_joined)
        reach_id_index = PNET_Functions.get_field_index("TARGET_FID", spatial_joined)
        point_id_index = PNET_Functions.get_field_index("SiteID", spatial_joined)
        tor_bor_index = PNET_Functions.get_field_index("TOR_BOR", spatial_joined)

        new_list = split_list_by_id(stream_seg_list, reach_id_index)
        to_delete_list = []
        keep_points_list = []

        # Check which segments we need to delete
        for segment in new_list:
            if delete_segment(segment, point_id_index, tor_bor_index, reach_id_index):
                to_delete_list.append(segment[0][reach_id_index])
            else:
                keep_points_list.append(segment[0][point_id_index])

        segments_layer = "Segments"
        arcpy.MakeFeatureLayer_management(stream_seg, segments_layer)

        # Delete the segments we need to from initial segments
        for to_delete in to_delete_list:
            arcpy.SelectLayerByAttribute_management(segments_layer, 'ADD_TO_SELECTION', 'FID = {}'.format(to_delete))

        # Save the reaches we want to keep
        arcpy.SelectLayerByAttribute_management(segments_layer, 'SWITCH_SELECTION')
        reach_save_location = os.path.join(output_folder, "Field_Reaches.shp")
        arcpy.CopyFeatures_management(segments_layer, reach_save_location)
        to_merge_reaches.append(reach_save_location)

        # Save the points we want to keep
        points_layer = "Points"
        arcpy.MakeFeatureLayer_management(points, points_layer)

        for to_keep in keep_points_list:
            arcpy.SelectLayerByAttribute_management(points_layer, 'ADD_TO_SELECTION', 'SiteID = {}'.format(to_keep))

        point_save_location = os.path.join(output_folder, "Field_Points.shp")
        arcpy.CopyFeatures_management(points_layer, point_save_location)
        to_merge_points.append(point_save_location)

        num_points = int(arcpy.GetCount_management(point_save_location)[0])
        num_reaches = int(arcpy.GetCount_management(reach_save_location)[0])

        # Check that everything was done correctly
        if (num_points/2) != num_reaches:
            arcpy.AddMessage("\t This watershed does not have one field reach per two field points!")

    arcpy.AddMessage("Saving ProjectWide...")
    projectwide_folder = os.path.join(root_folder, "00_ProjectWide", "Intermediates", "Reach_Editing", "Outputs")
    arcpy.Merge_management(to_merge_points, os.path.join(projectwide_folder, "Field_Points.shp"))
    arcpy.Merge_management(to_merge_reaches, os.path.join(projectwide_folder, "Field_Reaches.shp"))
    PNET_Functions.delete_temps(temps_to_delete)
    PNET_Functions.finish()


def split_list_by_id(segment_list, id_index):

    to_return = []
    current_seg = []
    previous_id = segment_list[0][id_index]

    for segment in segment_list:

        # Adding a segment to the same reach
        if segment[id_index] == previous_id:
            current_seg.append(segment)

        # Adding a new reach to the return list, then creating a new reach
        else:
            to_return.append(current_seg)
            current_seg = [segment]
            previous_id = segment[id_index]

    # This makes sure that the final reach gets added, because it may be missed in the for loop
    to_return.append(current_seg)

    # Returns a list of reaches, which each contain a list of segments, which each contain a list of field values
    return to_return


def delete_segment(segment, point_id, tor_bor, reach_id):

    # If this segment is not touching exactly two points, delete it
    if len(segment) != 2:
        return True

    # These hold data for the first and second point that the segment is touching
    point_a = segment[0]
    point_b = segment[1]

    # If the two points the segment is touching are from different sites, delete it
    if point_a[point_id] != point_b[point_id]:
        return True

    # Also delete if they are both TOR or both BOR
    if point_a[tor_bor] == point_b[tor_bor]:
        return True

    return False


def data_cleaning(root_folder):

    # Initialize variables and file locations
    arcpy.env.overwriteOutput = True

    watershed_folders = PNET_Functions.get_watershed_folders(root_folder)
    projectwide_output = os.path.join(root_folder, "00_ProjectWide", "Intermediates", "Extraction", "Inputs")
    temps_to_delete = []
    keep_fields = ["Shape", "FID", "SiteID", "RchID", "POINT_X", "POINT_Y", "SnapDist"]
    to_merge_reaches = []
    to_merge_points = []
    PNET_Functions.delete_old(os.path.join(root_folder, "00_ProjectWide", "Inputs", "Parameters"))


    PNET_Functions.delete_old(projectwide_output)

    for watershed in watershed_folders:
        arcpy.AddMessage("Starting {}...".format(watershed))

        # Get necessary files
        output_folder = os.path.join(watershed, "Intermediates", "Extraction", "Inputs")
        in_reaches = os.path.join(watershed, "Intermediates", "Reach_Editing", "Outputs", "Field_Reaches.shp")
        in_points = os.path.join(watershed, "Intermediates", "Reach_Editing", "Outputs", "Field_Points.shp")
        points_temp = os.path.join(output_folder, "p_temp.shp")
        reaches_temp = os.path.join(output_folder, "r_temp.shp")
        reaches_joined = os.path.join(output_folder, "r_join.shp")
        points_joined = os.path.join(output_folder, "p_join.shp")
        temps_to_delete.extend([points_temp, reaches_temp, reaches_joined, points_joined])
        points_final = os.path.join(output_folder, "Field_Points_Clean.shp")
        reaches_final = os.path.join(output_folder, "Field_Reaches_Clean.shp")

        # Add field for the length of the field reach
        arcpy.Copy_management(in_reaches, reaches_temp)
        field_to_add = "FldRchLen"
        keep_fields.append(field_to_add)
        field_names = [f.name for f in arcpy.ListFields(reaches_temp)]

        if field_to_add not in field_names:
            arcpy.AddField_management(reaches_temp, field_to_add, "DOUBLE")

        arcpy.CalculateField_management(reaches_temp, field_to_add, "!shape.length@meters!", "PYTHON_9.3", "")

        # Reduce points to only BOR points
        points_layer = "Points"
        arcpy.MakeFeatureLayer_management(in_points, points_layer)
        arcpy.SelectLayerByAttribute_management(points_layer, 'NEW_SELECTION', "\"TOR_BOR\" = \'BOR\'")
        arcpy.CopyFeatures_management(points_layer, points_temp)

        # Add all point data to the reaches
        arcpy.SpatialJoin_analysis(reaches_temp, points_temp, reaches_joined, "JOIN_ONE_TO_ONE")

        # Add all reach data to the points
        arcpy.SpatialJoin_analysis(points_temp, reaches_temp, points_joined, "JOIN_ONE_TO_ONE")

        # Only keep fields we need
        shapes = [points_joined, reaches_joined]
        for shape in shapes:

            # Removes all fields from the shapefile that are not in the above list of fields to keep
            field_names = [f.name for f in arcpy.ListFields(shape)]
            delete_fields = []
            for field in field_names:
                if field not in keep_fields:
                    delete_fields.append(field)

            arcpy.DeleteField_management(shape, delete_fields)

        # Save the points and reaches
        to_merge_points.append(arcpy.CopyFeatures_management(points_joined, points_final))
        to_merge_reaches.append(arcpy.CopyFeatures_management(reaches_joined, reaches_final))

    arcpy.AddMessage("Saving Projectwide...")
    arcpy.Merge_management(to_merge_points, os.path.join(projectwide_output, "Field_Points_Clean"))
    arcpy.Merge_management(to_merge_reaches, os.path.join(projectwide_output, "Field_Reaches_Clean"))

    PNET_Functions.delete_temps(temps_to_delete)
    PNET_Functions.finish()


def data_network_input(root_folder, data_networks_list_in):

    # Initialize variables and file locations
    arcpy.env.overwriteOutput = True

    watershed_folders = PNET_Functions.get_watershed_folders(root_folder)
    projectwide_output = os.path.join(root_folder, "00_ProjectWide", "Inputs", "Data_Networks")
    projectwide_network = os.path.join(root_folder, "00_ProjectWide",  "Inputs", "Stream_Network", "Stream_Network.shp")
    PNET_Functions.delete_old(projectwide_output)
    total_count = len(data_networks_list_in)

    network_names = []

    for _ in data_networks_list_in:
        network_names.append([])

    for data_network, network_slot in zip(data_networks_list_in, network_names):
        name = data_network.split("\\")[-1]
        new_name = name.replace(".shp", "")
        network_slot.append(new_name)
        network_slot.append(data_network)

    sorted_list = sorted(network_names, key=lambda s: s[0].lower())

    for watershed in watershed_folders:
        # Clear old data
        PNET_Functions.delete_old(os.path.join(watershed, "Inputs", "Data_Networks"))

    for current_count, network_data in enumerate(sorted_list):

        name = network_data[0]
        network = network_data[1]
        arcpy.AddMessage("\nSaving {} Files ({}/{})...".format(name, current_count+1, total_count))

        if '.shp' not in name:
            name += '.shp'

        for watershed in watershed_folders:

            arcpy.AddMessage("\tStarting " + watershed + "...")

            # Get network to clip by
            old_stream_network = os.path.join(watershed, "Inputs", "Stream_Network", "Stream_Network.shp")

            # Clip the current data network to this watershed
            new_network_save = os.path.join(watershed, "Inputs", "Data_Networks", name)
            arcpy.Clip_analysis(network, old_stream_network, new_network_save)


            # Don't create an empty shapefile
            if PNET_Functions.is_empty(new_network_save):
                arcpy.AddMessage("Did not save {}, as it was empty".format(new_network_save))
                arcpy.Delete_management(new_network_save)

        arcpy.AddMessage("\tSaving Projectwide...")
        new_network_save = os.path.join(projectwide_output, name)
        arcpy.Clip_analysis(network, projectwide_network, new_network_save)

    PNET_Functions.finish()


def data_network_extraction(root_folder, length_cutoff):

    # Initialize variables and file locations
    arcpy.env.overwriteOutput = True

    watershed_folders = PNET_Functions.get_watershed_folders(root_folder)
    projectwide_output = os.path.join(root_folder, "00_ProjectWide", "Intermediates", "Extraction", "Outputs")
    PNET_Functions.delete_old(projectwide_output)

    to_merge = []
    # Add a bunch of blank lists to the to_merge list, one space for each data network type
    for _ in get_data_networks(watershed_folders[0]):
        to_merge.append([])
    to_delete = []

    # This loops for every watershed
    for watershed_folder in watershed_folders:

        output_folder = os.path.join(watershed_folder, "Intermediates", "Extraction", "Outputs")

        network_list = get_data_networks(watershed_folder)

        arcpy.AddMessage("Starting " + watershed_folder + "...")
        for data_network_count, data_network in enumerate(network_list):
            if not PNET_Functions.is_empty(data_network):

                old_reaches = os.path.join(watershed_folder, "Intermediates",
                                           "Extraction", "Inputs", "Field_Reaches_Clean.shp")

                # Create a name for this data network so it can have a unique save location
                data_network_name = data_network.replace(os.path.join(watershed_folder, "Inputs", "Data_Networks"), "")
                data_network_name = data_network_name.replace(".shp", "")
                data_network_name = data_network_name.replace("\\", "")

                arcpy.AddMessage("\tStarting {}...".format(data_network_name))

                data_network_folder = PNET_Functions.make_folder(output_folder, data_network_name)
                PNET_Functions.delete_old(data_network_folder)

                reaches = os.path.join(data_network_folder, "Reaches_Temp.shp")

                to_delete.append(reaches)

                reaches_save = os.path.join(data_network_folder, data_network_name + "_Points_Extracted.shp")

                arcpy.CopyFeatures_management(old_reaches, reaches)

                # Clip the data network to the Field reaches. This is important for calculating the math later
                clip = os.path.join(data_network_folder, "Clip_Temp.shp")
                to_delete.append(clip)

                arcpy.Clip_analysis(data_network, reaches, clip)
                clipped_data_network = clip

                # Adds field CLIP_LEN, which is the length of the clipped data segment
                arcpy.AddField_management(clipped_data_network, "CLIP_LEN", "DOUBLE")
                arcpy.CalculateField_management(clipped_data_network, "CLIP_LEN", "!shape.length@meters!", "PYTHON_9.3", "")

                # These fields is unnecessary and causes issues with merging, so they are deleted
                field_names = [f.name for f in arcpy.ListFields(clipped_data_network)]
                fields_to_delete = ["Join_Count", "TARGET_FID", "Join_Cou_1"]
                for field in fields_to_delete:
                    if field in field_names:
                        arcpy.DeleteField_management(clipped_data_network, field)

                data_network_fields = PNET_Functions.get_fields(data_network)
                pnet_fields = PNET_Functions.get_fields(old_reaches)
                fields_to_keep = pnet_fields + data_network_fields



                # Extracts data from the data network to PIBO reaches using a weighted average system.
                extract_network(reaches, clipped_data_network, reaches_save, data_network_folder, pnet_fields)

                # Remove all unnecessary fields
                PNET_Functions.keep_fields(reaches_save, fields_to_keep)
                #remove_empty_fields(reaches_save, pnet_fields)

                # Delete any temporary shape files created
                PNET_Functions.delete_temps(to_delete)



                PNET_Functions.create_csv(os.path.join(data_network_folder, "{}.csv".format(data_network_name)), reaches_save)
                to_merge[data_network_count].append([reaches_save, data_network_name])

    # Iterate through to_merge, and save a point and network shapefile for each data network

    arcpy.AddMessage("Saving Projectwide...")
    for data_network_type in to_merge:
        to_merge_networks = []
        save_name = data_network_type[0][1]
        save_folder = PNET_Functions.make_folder(projectwide_output, save_name)
        for watershed in data_network_type:
            to_merge_networks.append(watershed[0])
        csv_save = arcpy.Merge_management(to_merge_networks,
                               os.path.join(save_folder, save_name + "_Points_Extracted.shp"))
        PNET_Functions.create_csv(os.path.join(save_folder, "{}.csv".format(save_name)), csv_save)

    PNET_Functions.finish()


def get_data_networks(watershed_folder):

    # Gets a list of all network shapefile locations
    to_return = []
    network_folder = os.path.join(watershed_folder, "Inputs", "Data_Networks")
    for r, d, f in os.walk(network_folder):
        for file in f:
            # This line makes sure it is a shapefile and also ignores the full BRAT network (As we only need perennial)
            if '.shp' in file and '.xml' not in file:
                to_return.append(os.path.join(r, file))

    return to_return


def extract_network(network, data_network, output, data_network_folder, fields_to_keep):

    to_delete = []

    # Create a shapefile to check how many data network segments each field reach overlaps
    spatial_temp = os.path.join(data_network_folder, "spatial_temp.shp")
    to_delete.append(spatial_temp)
    arcpy.SpatialJoin_analysis(network, data_network, spatial_temp, "JOIN_ONE_TO_ONE")
    network = spatial_temp

    # Create a shapefile of Field reaches that only overlap with one data_network segment
    join_one = "JoinOne"
    arcpy.MakeFeatureLayer_management(network, join_one)
    arcpy.SelectLayerByAttribute_management(join_one, 'NEW_SELECTION', 'Join_Count = 1')
    temp = os.path.join(data_network_folder, "JoinOne_Temp.shp")
    to_delete.append(temp)
    arcpy.CopyFeatures_management(join_one, temp)
    join_one = temp

    # Extracts data_network data onto the PIBO reaches with only one data_network segment
    temp2 = os.path.join(data_network_folder, "ExtractedOne_Temp.shp")
    to_delete.append(temp2)
    extracted_one = extract_singles(join_one, data_network, temp2, data_network_folder)
    to_delete.append(extracted_one)

    # Create a shapefile of PIBO reaches that only overlap with multiple data_network segments
    join_mult = "JoinMult"
    arcpy.MakeFeatureLayer_management(network, join_mult)
    arcpy.SelectLayerByAttribute_management(join_mult, 'NEW_SELECTION', 'Join_Count > 1')
    temp3 = os.path.join(data_network_folder, "JoinMult_Temp.shp")
    to_delete.append(temp3)
    arcpy.CopyFeatures_management(join_mult, temp3)
    join_mult = temp3

    # Checks to see how many PIBO reaches overlap multiple data_network segments
    num_rows = arcpy.GetCount_management(join_mult)
    num_rows = int(num_rows[0])

    # This makes sure that we are not trying to extract data onto a file with no reaches
    if num_rows > 0:

        # Extracts data_network data onto the PIBO reaches with only multiple data_network segments
        temp4 = os.path.join(data_network_folder, "ExtractMult_Temp.shp")
        to_delete.append(temp4)
        extracted_mult = extract_multiple(join_mult, data_network, temp4, fields_to_keep, data_network_folder)
        to_delete.append(extracted_mult)
        arcpy.Merge_management([extracted_one, extracted_mult], output)

    else:

        # No merging is necessary, since there were no multiple segment reaches
        arcpy.CopyFeatures_management(extracted_one, output)

    # Delete any temporary shape files created
    PNET_Functions.delete_temps(to_delete)

    # Return the shapefile with all PIBO reaches, now with data_network data
    return output


def extract_singles(network, data_network, temp, data_network_folder):

    # Performs a spatial join on the single segment PIBO reaches, adding data_network data
    arcpy.SpatialJoin_analysis(network, data_network, temp)
    # Add relevant extraction type fields
    arcpy.AddField_management(temp, "EXT_TYPE", "TEXT")
    arcpy.AddField_management(temp, "EXT_MATH", "TEXT")

    data_points = arcpy.CreateFeatureclass_management(data_network_folder, "Extracted_Points_Single.shp",
                                                      "POINT", temp, spatial_reference=temp)

    with arcpy.da.SearchCursor(temp, '*') as searcher:
        with arcpy.da.InsertCursor(data_points, '*') as inserter:
            for row in searcher:
                inserter.insertRow(row)

    return data_points


def extract_multiple(network, data_network, temp, fields_to_keep, data_network_folder):

    # Clean up the dataset so that we only keep fields we want
    field_names = [f.name for f in arcpy.ListFields(network)]
    fields_to_delete = ["Join_Count", "TARGET_FID", "Join_Cou_1"]
    for field in fields_to_delete:
        if field in field_names:
            arcpy.DeleteField_management(network, field)
    fields_to_keep += fields_to_delete
    PNET_Functions.keep_fields(network, fields_to_keep)

    # Creates a shapefile with an entry for every data_network segment that overlaps a PIBO reach
    arcpy.SpatialJoin_analysis(network, data_network, temp, "JOIN_ONE_TO_MANY")
    joined = temp
    field_names = [f.name for f in arcpy.ListFields(joined)]
    data_list = []

    # Turns the shapefile from before into a Python list. This is to minimize interaction with cursors.
    with arcpy.da.SearchCursor(joined, '*') as cursor:
        for row in cursor:
            to_add = []
            for count, field in enumerate(field_names):
                to_add.append(row[count])
            data_list.append(to_add)

    # Split the data list by PIBO reach, so that per reach calculations can be done.
    split_list = split_list_by_reach(data_list, field_names)

    # This is where all of the math happens. Each PIBO reach now has the necessary data_network data.
    input_list = combine_segments(split_list, field_names)

    # Add relevant extraction type fields
    arcpy.AddField_management(joined, "EXT_TYPE", "TEXT")
    arcpy.AddField_management(joined, "EXT_MATH", "TEXT")

    # Remove reaches that are repeats from the same join
    field_names = [f.name for f in arcpy.ListFields(joined)]
    if "TARGET_FID" in field_names:
        arcpy.DeleteIdentical_management(joined, "TARGET_FID")

    # Create a new points shapefile to save all of this data
    data_points = arcpy.CreateFeatureclass_management(data_network_folder, "Extracted_Points_Multiple.shp",
                                                      "POINT", joined, spatial_reference=joined)

    # Put extracted data on these points
    with arcpy.da.InsertCursor(data_points, '*') as cursor:
        for input_reach in input_list:
            cursor.insertRow(input_reach)

    return data_points


def split_list_by_reach(segment_list, fields):

    # Initialize Values
    reach = []
    reach_id_index = fields.index("""RchID""")
    return_list = []
    past_reach_id = segment_list[0][reach_id_index]
    need_last = True

    # This loop is to take the list of individual data_network segments, and put them into a new list, grouped by reach
    for seg in segment_list:

        # Adding a segment to the same reach
        if seg[reach_id_index] == past_reach_id:
            reach.append(seg)
            need_last = True

        # Adding a new reach to the return list, then creating a new reach
        else:
            return_list.append(reach)
            reach = [seg]
            past_reach_id = seg[reach_id_index]
            need_last = False

    # This makes sure that the final reach gets added, because it may be missed in the for loop
    if need_last:
        return_list.append(reach)

    # Returns a list of reaches, which each contain a list of segments, which each contain a list of field values
    return return_list


def print_split_list(split_list):
    # This exists only for troubleshooting purposes, prints the reach list in a readable way
    for reach in split_list:
        arcpy.AddMessage("Reach:")
        for segment in reach:
            arcpy.AddMessage("----------",)
            arcpy.AddMessage(segment)


def combine_segments(reach_list, fields):

    # Transpose the reach so that instead of being a list of segments,
    # it is a list of each field and its values within the reach
    for reach in reach_list:
        reach = transpose_reach(reach)

    # Adds and calculate a THRESHOLD field, which informs whether the segment is above or below the length threshold
    fields.append("THRESHOLD")
    reach_list = categorize_short(reach_list, fields)

    # Adds and calculate a TYPE field, which informs the segments relationship to other segments in the reach
    fields.append("TYPE")
    reach_list = categorize_type(reach_list, fields)

    # Adds and calculates the ACTION & MATH field, which informs what needs to be done to the segment for extraction
    fields.append("ACTION")
    fields.append("MATH")
    reach_list = categorize_action(reach_list, fields)

    # Deletes segments whose ACTION was tagged as 'Delete'
    reach_list = delete_unnecessary(reach_list)

    # Does all of the necessary math to calculate data_network values for each reach, based on values and the ACTION field
    reach_list = condense_to_single(reach_list, fields)

    # Removes all added fields (They shouldn't be in the shapefile), and returns the list to the expected format
    reach_list = cleanup(reach_list)

    # Returns a list of every reach, now complete with appropriate data_network data
    return reach_list


def transpose_reach(reach):

    # Flips a reach, so that each field now has its own list of values across the reach. This makes math much simpler.
    transposed = []
    for field_count in range(len(reach[0])):
        this_field = []
        for seg_count in range(len(reach)):
            this_field.append(reach[seg_count][field_count])
        transposed.append(this_field)
    return transposed


def categorize_short(reach_list, fields):

    # Populates the THRESHOLD field
    # Below: The segment is lower than the given length threshold
    # Above: The segment is higher than the given length threshold

    length_index = fields.index("""CLIP_LEN""")
    for reach in reach_list:
        for seg in reach:
            if seg[length_index] <= length_cutoff:
                seg.append("Below")
            else:
                seg.append("Above")
    return reach_list


def categorize_type(reach_list, fields):

    # Populates the TYPE field
    short_index = fields.index("""THRESHOLD""")
    # Loops for each reach in the list
    for reach in reach_list:
        short_list = []
        # Adds the THRESHOLD values for this reach into list
        for seg_count in range(len(reach)):
            short_list.append(reach[seg_count][short_index])
        # Calculates the reach TYPE based off of the reach's THRESHOLD values
        extraction_type = parse_short_list(short_list)
        # Add the TYPE field values into the reach
        for seg in reach:
            seg.append(extraction_type)

    # Return a list of reaches, now with the TYPE field populated
    return reach_list


def categorize_action(reach_list, fields):

    # Categorizes the ACTION and MATH Field
    # Keep: Keep this segment for calculations
    # Delete: Delete this segment before calculations

    short_index = fields.index("""THRESHOLD""")
    type_index = fields.index("""TYPE""")
    for reach in reach_list:
        for seg in reach:
            seg_type = seg[type_index]
            seg_short = seg[short_index]

            if seg_type == "All" or seg_type == "None":
                action = "Keep"
                math = "Yes"
            elif seg_type == "Multiple":
                if seg_short == "Above":
                    action = "Keep"
                    math = "Yes"
                else:
                    action = "Delete"
                    math = "No"
            else:
                if seg_short == "Above":
                    action = "Keep"
                    math = "No"
                else:
                    action = "Delete"
                    math = "No"

            seg.append(action)
            seg.append(math)

    return reach_list


def parse_short_list(short_list):

    # Parses a reach by how many segments are under the length threshold
    # All: All segments are above the threshold
    # Multiple: Multiple, but not all segments are above the threshold
    # Single: A single segment is above the threshold
    # None: No segments are above the threshold

    if len(short_list) <= 2:
        if "Below" not in short_list:
            return "All"
        elif "Above" in short_list:
            return "Single"
        else:
            return "None"
    else:
        if "Above" not in short_list:
            return "None"
        elif "Below" not in short_list:
            return "All"
        a_count = short_list.count("Above")
        if a_count == 1:
            return "Single"
        else:
            return "Multiple"


def delete_unnecessary(reach_list):

    delete_list = []

    # Create a list of every segment that needs to be deleted
    for reach_index, reach in enumerate(reach_list):
        for seg_index, seg in enumerate(reach):
            if "Delete" in seg:
                delete_list.append([reach_index, seg_index])

    # Reverse the list so that indexes don't get ruined as we delete
    delete_list.reverse()

    # Delete all lists that has 'Delete' as their action
    for index in delete_list:
        reach = index[0]
        seg = index[1]
        reach_list[reach].pop(seg)

    return reach_list


def condense_to_single(reach_list, fields):

    length_index = fields.index("""CLIP_LEN""")

    new_return = []

    # Condenses each reach into a single segment with all averaged values
    for reach in reach_list:

        # This checks if we actually need to do any math
        if "Single" not in reach[0]:

            condensed_seg = [[]]

            # This will loop to do the calculations for each field
            for field_index in range(len(fields)):

                this_field = []
                length_list = []

                # This loops to fill the this_field list with the each value in that field for this reach
                # Also populates the length_list, which holds the lengths for each segment.
                for seg_index in range(len(reach)):

                    this_field.append(reach[seg_index][field_index])
                    length_list.append(reach[seg_index][length_index])

                # Condenses the current field into one value, adds it to the list for the current reach
                condensed_seg[0].append(parse_multi_seg(this_field, length_list))

            # Adds the reach, now only one set of values, to the larger return list
            new_return.append(condensed_seg)

        # Since it is the only good segment it its reach, we can just use these values directly
        else:
            new_return.append(reach)

    # Return a list of reaches, all with a single set of values
    return new_return


def parse_multi_seg(to_parse, length_list):

    # This checks to see if everything it was handed to parse is the same
    if len(set(to_parse)) == 1:
        # Every segment is the same in this field, so just return the first one
        return to_parse[0]

    # This checks to see if the field that is being parsed is a string
    elif isinstance(to_parse[0], str) or isinstance(to_parse[0], unicode):
        # Return the string from the longest segment, as that has the most influence
        max_index = length_list.index(max(length_list))
        return to_parse[max_index]

    # This checks to see if the field that is being parsed is a number
    elif isinstance(to_parse[0], int) or isinstance(to_parse[0], float):
        return weighted_average(to_parse, length_list)

    # This shouldn't ever really happen.
    else:
        return to_parse[0]


def weighted_average(to_parse, length_list):

    # Converts everything to floats
    to_parse = [float(s) for s in to_parse]
    length_list = [float(s) for s in length_list]

    # Remove negative values
    new_values = [value for value in to_parse if value > 0]
    new_lengths = []
    for keep in new_values:
        new_lengths.append(length_list[to_parse.index(keep)])

    if len(new_lengths) > 1:

        # Calculates the relative weight of each segment, based on its proportion of the total PIBO reach length
        weight_list = []
        for length in new_lengths:
            weight_list.append(length/sum(new_lengths))

        # Multiplies the weights by their values for each segment
        sum_list = []
        for data_value, weight in zip(new_values, weight_list):
            sum_list.append(data_value*weight)

        # Returns the final weighted average for the segment
        to_return = sum(sum_list)

    else:
        # Return the value from the longest segment
        to_return = to_parse[length_list.index(max(length_list))]

    if to_return < 0:
        arcpy.AddMessage(to_return)
    return to_return


def cleanup(reach_list):

    # Changes list format from reaches containing a single segment to just a list of reaches
    cleaned_list = []
    for reach in reach_list:
        cleaned_list.append(reach[0])

    # Removes the THRESHOLD and ACTION fields from the list entirely
    for reach in cleaned_list:
        reach.pop(-2)
        reach.pop(-3)

    return cleaned_list


def reach_merging(root_folder):
    # Initialize variables and file locations
    arcpy.env.overwriteOutput = True

    watershed_folders = PNET_Functions.get_watershed_folders(root_folder)
    projectwide_output = os.path.join(root_folder, "00_ProjectWide", "Outputs", "Extracted_Data")
    PNET_Functions.delete_old(projectwide_output)
    to_merge_points = []
    req_fields = ["RchID", "FID", "Shape"]

    # This loops for each watershed folder
    for watershed in watershed_folders:
        arcpy.AddMessage("Working on {}...".format(watershed))

        # Initialize list of all unique data networks within this watershed
        point_list = get_data_points(watershed)
        output_folder = os.path.join(watershed, "Outputs", "Extracted_Data")
        PNET_Functions.delete_old(output_folder)

        # Create temporary shapefiles to store spatially joined data
        all_joined = os.path.join(output_folder, "temp.shp")

        # Join the first and second network's data together, and store them into a temporary shapefile
        arcpy.AddMessage("\t Merging first points...")

        arcpy.Copy_management(point_list[0], all_joined)
        all_fields = PNET_Functions.get_fields(all_joined)
        for field in req_fields:
            if field in all_fields:
                all_fields.remove(field)

        point_list.pop(0)

        # Check to make sure there are still networks to join
        if len(point_list) > 0:

            # This repeats for each of the two remaining networks
            for data in point_list:

                arcpy.AddMessage("\t\tMerging more points...")
                data_temp = os.path.join(output_folder, "data_temp.shp")
                arcpy.Copy_management(data, data_temp)
                data = data_temp
                remove_existing_fields(all_fields, data)

                # Join the current network to the previous network containing all other data
                arcpy.JoinField_management(all_joined, "RchID", data, "RchID")
                arcpy.DeleteField_management(all_joined, "RchID_1")
                all_fields = PNET_Functions.get_fields(all_joined)
                for field in req_fields:
                    if field in all_fields:
                        all_fields.remove(field)

        # Save the output into the correct folder
        save = arcpy.Copy_management(all_joined,
                                     os.path.join(output_folder, "Extraction_Merge_Points.shp"))

        to_merge_points.append(save)

        PNET_Functions.create_csv(os.path.join(output_folder, "All_Data.csv"), save)

        # Delete both temp shapefiles
        arcpy.Delete_management(all_joined)
        arcpy.Delete_management(data_temp)

    arcpy.AddMessage("Working on Projectwide...")

    make_csv = arcpy.Merge_management(to_merge_points,
                           os.path.join(projectwide_output, "Extraction_Merge_Points.shp"))
    PNET_Functions.create_csv(os.path.join(projectwide_output, "All_Data.csv"), make_csv)
    PNET_Functions.finish()


def get_data_points(watershed_folder):

    # Gets a list of all network shapefile locations
    to_return = []
    network_folder = os.path.join(watershed_folder, "Intermediates", "Extraction", "Outputs")
    data_network_list = PNET_Functions.get_folder_list(network_folder, False)

    for folder in data_network_list:

        for r, d, f in os.walk(folder):
            for file in f:
                # This line makes sure it is a shapefile
                if '.shp' in file and 'Reaches' not in file and '.xml' not in file and '.lock' not in file:
                    to_return.append(os.path.join(r, file))
    to_keep = []
    for file in to_return:
        if not PNET_Functions.is_empty(file):
            to_keep.append(file)

    return to_keep


def remove_existing_fields(all_fields_list, shapefile):

    # Removes all fields tht are already part of the merged shapefile
    cur_fields = PNET_Functions.get_fields(shapefile)
    deleted_fields = []
    for cur_field in cur_fields:
        if cur_field in all_fields_list:
            arcpy.DeleteField_management(shapefile, cur_field)
            deleted_fields.append(cur_field)

    return deleted_fields


def calculate_d50(root_folder):
    discharge_field = "iHyd_Q2"
    bankfull_field = "BFWIDTH"
    slope_field = "iGeo_Slope"
    input_fields = [discharge_field, bankfull_field, slope_field]

    # Initialize variables and file locations
    arcpy.env.overwriteOutput = True
    watershed_folders = PNET_Functions.get_watershed_folders(root_folder)

    # Setup projectwide data
    data_path = r"Outputs/Extracted_Data/Extraction_Merge_Points.shp"
    watershed_folders.append(os.path.join(root_folder, "00_ProjectWide"))

    for watershed in watershed_folders:

        # get filepath
        arcpy.AddMessage("Working on {}...".format(watershed))
        watershed_extracted = os.path.join(watershed, data_path)

        # Check to make sure we have the necessary fields
        existing_fields = PNET_Functions.get_fields(watershed_extracted)
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
                    d50_03, d50_04 = calculate_equation(row[0], row[1], row[2])
                    # Update with new d50 values
                    cursor.updateRow([row[0], row[1], row[2], d50_03, d50_04])

            # Update CSV
            PNET_Functions.create_csv(os.path.join(watershed, "Outputs", "Extracted_Data", "All_Data.csv"),
                                      watershed_extracted)


def calculate_equation(discharge, bankfull, slope, n=.035, tc03=.03, tc04=.04):
    # Calculate using TC03
    tco3_d50 = ((997 * 9.81) * n * ((discharge - .0283168) ** (3 / 5)) * (bankfull ** (-3 / 5)) * (slope ** (7 / 10))) / \
               ((2650 - 997) * 9.81 * tc03)

    # Calculate using TC04
    tco4_d50 = ((997 * 9.81) * n * ((discharge - .0283168) ** (3 / 5)) * (bankfull ** (-3 / 5)) * (slope ** (7 / 10))) / \
               ((2650 - 997) * 9.81 * tc04)

    return tco3_d50, tco4_d50


def numerical_comparisons(root_folder, field_db, input_field_csv):
    # Initialize variables and file locations
    arcpy.env.overwriteOutput = True
    watershed_folders = PNET_Functions.get_watershed_folders(root_folder)

    # Setup projectwide data

    projectwide_output = PNET_Functions.make_folder(os.path.join(root_folder, "00_ProjectWide", "Outputs", "Comparisons"), "Numerical")
    save_db(field_db, os.path.join(root_folder, "00_ProjectWide"))
    PNET_Functions.delete_old(projectwide_output)

    keep_fields = ["FID", "Shape", "POINT_X", "POINT_Y", "SnapDist", "FldRchLen",
                   "EcoRgn_L4" ,"EcoRgn_L3" ,"HUC8" ,"NAME" ,"StreamName",
                   "PRECIP", "DRAREA", "iGeo_ElMax", "iGeo_ElMin"]

    to_merge = []

    # Set the field lists to the values from the fields value
    pnet_fields, field_db_fields, new_fields_initial = read_field_csv(input_field_csv)

    for watershed in watershed_folders:

        old_pnet_fields = pnet_fields
        old_field_db_fields = field_db_fields
        old_new_fields_initial = new_fields_initial

        arcpy.AddMessage("Working on {}...".format(watershed))
        arcpy.AddMessage("\t Combining Data...")

        # Setup watershed data
        watershed_output = PNET_Functions.make_folder(os.path.join(watershed, "Outputs", "Comparisons"), "Numerical")
        PNET_Functions.delete_old(watershed_output)

        # Get the CSV with extracted PNET data
        watershed_pnet = os.path.join(watershed, "Outputs", "Extracted_Data", "All_Data.csv")

        # Get data from the PNET output
        pnet_data_list = PNET_Functions.csv_to_list(watershed_pnet)

        # Find certain PNET indexes in the PNET output
        id_pnet = pnet_data_list[0].index("""RchID""")
        pnet_indexes = []
        missing_field_indexes = []
        for pnet_field in old_pnet_fields:
            if pnet_field in pnet_data_list[0]:
                pnet_indexes.append(pnet_data_list[0].index(pnet_field))
            else:
                missing_field_indexes.append(old_pnet_fields.index(pnet_field))

        # remove headers
        pnet_data_list.pop(0)

        # Create a list with only necessary data
        pnet_compare_list = []
        for row in pnet_data_list:
            to_add = []
            # Add id column
            to_add.append(row[id_pnet])
            # Add any other columns
            for index in pnet_indexes:
                to_add.append(row[index])
            pnet_compare_list.append(to_add)

        # Get the CSV with Field data
        watershed_db = save_db(field_db, watershed)

        # Get data from the field database
        field_data_list = PNET_Functions.csv_to_list(watershed_db)

        # Find certain field indexes in the field database
        id_field_db = field_data_list[0].index("""RchID""")
        field_indexes_db = []
        for field_db_field in old_field_db_fields:
            if old_field_db_fields.index(field_db_field) not in missing_field_indexes:
                field_indexes_db.append(field_data_list[0].index(field_db_field))

        # remove headers
        field_data_list.pop(0)

        # Create a list with only necessary data
        field_compare_list = []
        for row in field_data_list:
            to_add = []
            # Add id column
            to_add.append(row[id_field_db])
            # Add any other columns
            for index in field_indexes_db:
                to_add.append(row[index])
            field_compare_list.append(to_add)

        # Make list of new fields
        new_fields = ["""RchID"""]
        for new_field in old_new_fields_initial:
            if old_new_fields_initial.index(new_field) not in missing_field_indexes:
                # make sure the field can fit into an arcmap field
                # This is where PNET data will go
                new_fields.append("pn_" + new_field[:7])
                # This is where field database data will go
                new_fields.append("fd_" + new_field[:7])
                # This is where actual difference data will go
                #new_fields.append("df_" + new_field[:7])
                # This is where percent difference data will go
                #new_fields.append("pf_" + new_field[:7])
                # This is where ratio data will go
                #new_fields.append("ro_" + new_field[:7])


        # Perform data comparisons

        both_compare_list = [new_fields]

        arcpy.AddMessage("\t Creating New Fields...")

        for pnet_row in pnet_compare_list:

            new_row = []
            # Get the ID of the current row
            current_site = pnet_row[0]


            # Find the corresponding row in the field data list
            for db_row_num, db_row in enumerate(field_compare_list):
                # If the two site are the same
                if db_row[0] == current_site:
                    field_row = db_row
                    break

            # Add the reach ID to our new row
            new_row.append(pnet_row[0])

            # Prepare to iterate through each column of data, skipping rchID
            pnet_iter = iter(pnet_row)
            field_iter = iter(field_row)
            next(pnet_iter)
            next(field_iter)

            for pnet_data, field_data, in zip(pnet_iter, field_iter):

                # Make sure that the data is not missing
                if pnet_data != "" and field_data != "":

                    # Add data into the new row
                    pnet_num = float(pnet_data)
                    field_num = float(field_data)
                    new_row.append(pnet_num)
                    new_row.append(field_num)

                    # Add actual difference field
                    #new_row.append(pnet_num-field_num)

                    # Add percent difference field
                    #if field_num > 0 or field_num < 0:
                    #     if pnet_num > field_num:
                    #        new_row.append((pnet_num-field_num)/pnet_num)
                    #    else:
                    #        new_row.append((field_num-pnet_num)/field_num)
                    #     #Add ratio field
                    #    new_row.append(float(pnet_num/field_num))
                    #else:
                    #    new_row.append(-999)


                else:
                    new_row += [-999, -999]

            both_compare_list.append(new_row)

        # Add in data for each of the other PNET fields
        pnet_data_list = PNET_Functions.csv_to_list(watershed_pnet)
        for row_num, row in enumerate(both_compare_list):
            # Add data from each PNET field
            data_to_add = []
            for add_field in keep_fields:
                if add_field in pnet_data_list[0]:
                    this_index = pnet_data_list[0].index(add_field)
                    data_to_add.append(pnet_data_list[row_num][this_index])
            both_compare_list[row_num] = data_to_add + row

        # Create a new shapefile to hold data
        template = os.path.join(watershed, "Outputs", "Extracted_Data", "Extraction_Merge_Points.shp")
        comparison_points = arcpy.CreateFeatureclass_management(watershed_output, "Numerical_Comparison_Points.shp",
                                                                "POINT", spatial_reference=template)

        # Add in new fields to the shapefile
        for count, (field, example) in enumerate(zip(both_compare_list[0], both_compare_list[1])):
            arcpy.AddMessage("\t\t Adding Field {} ({}/{})...".format(field, count+1, len(both_compare_list[0])))
            # Make sure we are not adding in any already existing default fields
            shapefile_fields = PNET_Functions.get_fields(comparison_points)
            if field not in shapefile_fields:
                # Decide to add a text or float field
                if isinstance(example, str):
                    arcpy.AddField_management(comparison_points, field, "TEXT")
                else:
                    arcpy.AddField_management(comparison_points, field, "FLOAT")
            elif count > 2:
                arcpy.AddMessage("\t\t\t Reminder: All new name fields need to be unique within the first 7 characters")

        # Skip headers
        iter_list = iter(both_compare_list)
        next(iter_list)

        # remove useless field
        arcpy.DeleteField_management(comparison_points, "Id")

        arcpy.AddMessage("\t Creating Shapefile...")

        # Add in data to the shapefile
        with arcpy.da.InsertCursor(comparison_points, '*') as inserter:
            with arcpy.da.SearchCursor(template, '*') as searcher:
                for row, search_row in zip(iter_list, searcher):
                    row[1] = search_row[1]
                    inserter.insertRow(row)

        to_merge.append(comparison_points)

        # Save as CSV
        PNET_Functions.create_csv(os.path.join(watershed_output, "Numerical_Comparison_Data.csv"), comparison_points)

    arcpy.AddMessage('Saving ProjectWide...')
    merged = arcpy.Merge_management(to_merge, os.path.join(projectwide_output, "Numerical_Comparison_Points.shp"))
    PNET_Functions.create_csv(os.path.join(projectwide_output, "Numerical_Comparison_Data.csv"), merged)


def save_db(database, main_folder):
    save_loc = os.path.join(main_folder, "Inputs", "Database", "Field_Database.csv")
    shutil.copyfile(database, save_loc)
    return save_loc


def is_csv(file):
    return file.endswith('.csv')


def read_field_csv(file):

    input_field_list = PNET_Functions.csv_to_list(file)

    # remove headers
    input_field_list.pop(0)

    list_a, list_b, list_c = [], [], []

    for unique_field in input_field_list:
        list_a.append(unique_field[0])
        list_b.append(unique_field[1])
        list_c.append(unique_field[2])

    return list_a, list_b, list_c


def categorical_comparisons(root_folder, input_comparison_field_csv):
    # Initialize variables and file locations
    arcpy.env.overwriteOutput = True
    watershed_folders = PNET_Functions.get_watershed_folders(root_folder)

    # Setup projectwide data
    projectwide_output = PNET_Functions.make_folder(os.path.join(root_folder, "00_ProjectWide", "Outputs", "Comparisons"), "Categorical")
    projectwide_database = os.path.join(root_folder, "00_ProjectWide", "Inputs", "Database", "Field_Database.csv")
    PNET_Functions.delete_old(projectwide_output)

    keep_fields = ["FID", "Shape", "POINT_X", "POINT_Y", "SnapDist", "FldRchLen",
                   "EcoRgn_L4", "EcoRgn_L3", "HUC8", "NAME", "StreamName",
                   "PRECIP", "DRAREA", "iGeo_ElMax", "iGeo_ElMin"]



    #  set the field lists to the values from the file
    # meta_group_field, meta_group_field_name, group_field, group_field_name, field_db_fields = read_comparison_field_csv(input_field_csv)

    graphs = read_field_csv_new(input_field_csv)

    for graph in graphs:

        to_merge = []

        meta_group_field = graph[0]
        meta_group_field_name = graph[1]
        group_field = graph[2]
        group_field_name = graph[3]
        field_db_fields = graph[4]

        arcpy.AddMessage("Graphing {}...".format(group_field_name))

        if meta_group_field and group_field_name:
            meta_exists = True
        else:
            meta_exists = False

        for watershed in watershed_folders:

            arcpy.AddMessage("\tWorking on {}...".format(watershed))

            # Setup watershed data
            watershed_output = PNET_Functions.make_folder(os.path.join(watershed, "Outputs", "Comparisons"), "Categorical")
            PNET_Functions.delete_old(watershed_output)

            # Get the CSV with Field data
            watershed_db = projectwide_database

            # Get data from the field database
            field_data_list = PNET_Functions.csv_to_list(watershed_db)

            # Find certain field indexes in the field database

            id_field_db = field_data_list[0].index("""RchID""")
            field_indexes_db = []
            for field_db_field in field_db_fields:
                field_indexes_db.append(field_data_list[0].index(field_db_field))

            # remove headers
            field_data_list.pop(0)

            # Create a list with only necessary data
            field_compare_list = []
            for row in field_data_list:
                to_add = []
                # Add id column
                to_add.append(row[id_field_db])
                # Add any other columns
                for index in field_indexes_db:
                    to_add.append(row[index])
                field_compare_list.append(to_add)

            # Get the CSV with extracted PNET data
            watershed_pnet = os.path.join(watershed, "Outputs", "Extracted_Data", "All_Data.csv")

            # Get data from the PNET output
            pnet_data_list = PNET_Functions.csv_to_list(watershed_pnet)

            # Find certain PNET indexes in the PNET output
            id_pnet = pnet_data_list[0].index("""RchID""")
            if group_field not in pnet_data_list[0]:
                arcpy.AddMessage("Could not complete plots for {}, could not find {} field".format(watershed, group_field))
            elif meta_exists and meta_group_field not in pnet_data_list[0]:
                arcpy.AddMessage("Could not complete plots for {}, could not find {} field".format(watershed, meta_group_field))
            else:
                group_pnet = pnet_data_list[0].index(group_field)
                if meta_exists:
                    meta_group_pnet = pnet_data_list[0].index(meta_group_field)

                # remove headers
                pnet_data_list.pop(0)

                # Create a list with only necessary data
                pnet_compare_list = []
                for row in pnet_data_list:
                    to_add = []
                    # Add id column
                    to_add.append(row[id_pnet])
                    # Add grouping columns
                    if meta_exists:
                        to_add.append(row[meta_group_pnet])

                    to_add.append(row[group_pnet])
                    # Add this row to the overall list
                    pnet_compare_list.append(to_add)

                # Make list of new fields
                if meta_exists:
                    new_fields = ["""RchID""", meta_group_field_name, group_field_name]
                else:
                    new_fields = ["""RchID""", group_field_name]

                for new_field in field_db_fields:
                    # This is where field data will go
                    new_fields.append("Y_" + new_field[:8])

                # Perform data comparisons

                both_compare_list = [new_fields]

                for pnet_row in pnet_compare_list:
                    new_row = []
                    # Get the ID of the current row
                    current_site = pnet_row[0]
                    # Find the corresponding row in the field data list
                    for db_row_num, db_row in enumerate(field_compare_list):
                        # If the two site are the same
                        if db_row[0] == current_site:
                            field_row = db_row
                            break

                    # Add the reach ID to our new row
                    new_row.append(pnet_row[0])
                    # Add the group/metagroup field to our new row
                    new_row.append(pnet_row[1])
                    if meta_exists:
                        # Add the metagroup to our new row
                        new_row.append(pnet_row[2])

                    # Prepare to iterate through each column of data, skipping rchID
                    field_iter = iter(field_row)
                    next(field_iter)

                    for field_data in field_iter:

                        # Make sure that the data is not missing
                        if field_data != "":

                            # Add data into the new row
                            field_num = float(field_data)
                            new_row.append(field_num)

                        else:
                            new_row += 0

                    both_compare_list.append(new_row)

                # Add in data for each of the other PNET fields (That were created in previous steps)
                pnet_data_list = PNET_Functions.csv_to_list(watershed_pnet)
                for row_num, row in enumerate(both_compare_list):
                    # Add data from each PNET field
                    data_to_add = []
                    for add_field in keep_fields:
                        if add_field in pnet_data_list[0]:
                            this_index = pnet_data_list[0].index(add_field)
                            data_to_add.append(pnet_data_list[row_num][this_index])
                    both_compare_list[row_num] = data_to_add + row


                # Create a new shapefile to hold data
                template = os.path.join(watershed, "Outputs", "Extracted_Data", "Extraction_Merge_Points.shp")
                comparison_points = arcpy.CreateFeatureclass_management(watershed_output, "Categorical_Comparison_Points.shp",
                                                                        "POINT", spatial_reference=template)
                to_merge.append(comparison_points)

                # Add in new fields to the shapefile
                for field, example in zip(both_compare_list[0], both_compare_list[1]):
                    # Make sure we are not adding in any already existing default fields
                    shapefile_fields = PNET_Functions.get_fields(comparison_points)
                    if field not in shapefile_fields:
                        # Decide to add a text or float field
                        if isinstance(example, str):
                            arcpy.AddField_management(comparison_points, field[:10], "TEXT")
                        else:
                            arcpy.AddField_management(comparison_points, field[:10], "FLOAT")

                # Skip headers
                iter_list = iter(both_compare_list)
                next(iter_list)

                # remove useless field
                arcpy.DeleteField_management(comparison_points, "Id")

                # Add in data to the shapefile
                with arcpy.da.InsertCursor(comparison_points, '*') as inserter:
                    with arcpy.da.SearchCursor(template, '*') as searcher:
                        for row, search_row in zip(iter_list, searcher):
                            # Steal Shape and FID data from template
                            row[0] = search_row[0]
                            row[1] = search_row[1]
                            # Add in row
                            inserter.insertRow(row)

                # Save as CSV
                PNET_Functions.create_csv(os.path.join(watershed_output, "Categorical_Comparison_Data.csv"), comparison_points)

                # Get a list of all the different metagroup types
                if meta_exists:

                    metagroup_types = unique_values(comparison_points, meta_group_field_name[:10])

                    # Make a folder, shapefile, and plots for every metagroup
                    if " " in metagroup_types:
                        metagroup_types.remove(" ")

                    for metagroup in metagroup_types:

                        # Create a new folder for only data in this meta group
                        plot_folder = PNET_Functions.make_folder(watershed_output, "{}_{}".format(meta_group_field_name.title(), metagroup.title()))
                        PNET_Functions.delete_old(plot_folder)

                        # Create a shapefile with only data we want to look at
                        layer_name = 'temp'
                        new_shapefile = os.path.join(plot_folder, '{}_{}_Comparison.shp'.format(meta_group_field_name.title(), metagroup.title()))
                        arcpy.MakeFeatureLayer_management(comparison_points, layer_name)
                        query = '{} = \'{}\''.format(meta_group_field_name[:10], metagroup)
                        arcpy.SelectLayerByAttribute_management(layer_name, 'NEW_SELECTION', query)
                        arcpy.CopyFeatures_management(layer_name, new_shapefile)

                        # Create plots for this data
                        create_plots(new_shapefile, group_field_name, field_db_fields, plot_folder, metagroup, meta_group_field_name)
                else:

                    plot_folder = PNET_Functions.make_folder(watershed_output, "{}".format(group_field_name.title()))
                    PNET_Functions.delete_old(plot_folder)

                    # Create a shapefile with only data we want to look at
                    layer_name = 'temp'
                    new_shapefile = os.path.join(plot_folder, '{}_Comparison.shp'.format(group_field_name.title()))
                    arcpy.MakeFeatureLayer_management(comparison_points, layer_name)
                    arcpy.CopyFeatures_management(layer_name, new_shapefile)

                    # Create plots for this data
                    create_plots(new_shapefile, group_field_name, field_db_fields, plot_folder)

                arcpy.Delete_management(new_shapefile)


        # Do projectwide
        arcpy.AddMessage('\tSaving ProjectWide...')
        save_loc = os.path.join(projectwide_output, "Categorical_Comparison_Points_{}.shp".format(group_field_name))
        merged = arcpy.Merge_management(to_merge, save_loc)
        PNET_Functions.create_csv(os.path.join(projectwide_output, "Categorical_Comparison_Data.csv"), merged)

        if meta_exists:

            # Get a list of all the different metagroup types
            metagroup_types = unique_values(merged, meta_group_field_name[:10])

            # Make a folder, shapefile, and plots for every metagroup
            if " " in metagroup_types:
                metagroup_types.remove(" ")

            for metagroup in metagroup_types:
                # Create a new folder for only data in this meta group
                plot_folder = PNET_Functions.make_folder(projectwide_output, "{}_{}".format(meta_group_field_name.title(), metagroup.title()))
                PNET_Functions.delete_old(plot_folder)

                # Create a shapefile with only data we want to look at
                layer_name = 'temp'
                new_shapefile = os.path.join(plot_folder,
                                             '{}_{}_Comparison.shp'.format(meta_group_field_name.title(), metagroup.title()))
                arcpy.MakeFeatureLayer_management(merged, layer_name)
                query = '{} = \'{}\''.format(meta_group_field_name[:10], metagroup)
                arcpy.SelectLayerByAttribute_management(layer_name, 'NEW_SELECTION', query)
                arcpy.CopyFeatures_management(layer_name, new_shapefile)

                # Create plots for this data
                create_plots(new_shapefile, group_field_name, field_db_fields, plot_folder, metagroup, meta_group_field_name)

        else:

            plot_folder = PNET_Functions.make_folder(projectwide_output, "{}".format(group_field_name.title()))
            PNET_Functions.delete_old(plot_folder)

            # Create a shapefile with only data we want to look at
            layer_name = 'temp'
            new_shapefile = os.path.join(plot_folder, '{}_Comparison.shp'.format(group_field_name.title()))
            arcpy.MakeFeatureLayer_management(merged, layer_name)
            arcpy.CopyFeatures_management(layer_name, new_shapefile)

            # Create plots for this data
            create_plots(new_shapefile, group_field_name, field_db_fields, plot_folder)

        arcpy.Delete_management(new_shapefile)
        arcpy.Delete_management(merged)


def create_plots(data_shapefile, group_field, y_axis_fields, out_folder, metagroup = "", metagroup_name = ""):

    for y_axis_field in y_axis_fields:
        try:
            labels, all_data = get_data(data_shapefile, group_field, y_axis_field)
            new_labels = []
            for entry, label in zip(all_data, labels):
                n = len(entry)
                new_label = "[{}] ".format(n) + label
                new_labels.append(new_label)

            # set up plot
            fig, ax = plt.subplots(nrows=1, ncols=1, figsize=(9, 9))
            bplot = ax.boxplot(all_data,
                               vert=True,  # vertical box alignment
                               labels=new_labels)  # will be used to label x-ticks
            if metagroup != "":
                ax.set_title('{} values for all {} groups\n [When {} = {}]'
                              .format(y_axis_field.title(), group_field.title(), metagroup_name.title(), metagroup.title()))
            else:
                ax.set_title('{} values for all {} groups'
                              .format(y_axis_field.title(), group_field.title()))

            ax.yaxis.grid(True)
            ax.set_xlabel('{} Category'.format(group_field.title()))
            ax.set_ylabel('{} Value'.format(y_axis_field.title()))
            plt.xticks(rotation=90)

            # save plot
            plot_name = os.path.join(out_folder, "{}_Plot.png".format(y_axis_field.title()))
            plt.savefig(plot_name, bbox_inches='tight')
            plt.close()
        except:
            arcpy.AddMessage("\t\tCould not plot {}".format(y_axis_field))


def get_data(data_shapefile, group_field, y_axis_field):

    # Pull comparison values from the comparison points shapefile
    actual_group_field = group_field[:10]
    actual_y_axis_field = "Y_" + y_axis_field[:8]

    groups_list = unique_values(data_shapefile, actual_group_field)

    if " " in groups_list:
        groups_list.remove(" ")

    if "" in groups_list:
        groups_list.remove("")

    data = []

    for group in groups_list:

        query = '{} = \'{}\''.format(actual_group_field, group)
        group_data = arcpy.da.FeatureClassToNumPyArray(data_shapefile, actual_y_axis_field, query).astype(np.float)

        # Remove negatives and zeros
        group_data = group_data[np.where(group_data > 0.0)]

        data.append(group_data)

    return groups_list, data


def plot_points(x, y, axis):

    axis.scatter(x, y, color="darkred", label="Field Sites", alpha=.4)


def plot_regression(x, y, axis, new_max):

    # calculate regression
    regression = stat.linregress(x, y)
    model_x = np.arange(0.0, new_max, new_max/10000)
    model_y = regression.slope * model_x + regression.intercept
    # plot regression line
    axis.plot(model_x, model_y,  color='black', linewidth=2.0, linestyle='-', label='Regression line')
    # calculate prediction intervals and plot as shaded areas
    n = len(x)

    return regression.rvalue**2, regression.slope, regression.intercept


def read_field_csv_new(file):
    input_field_list = PNET_Functions.csv_to_list(file)

    # remove headers
    input_field_list.pop(0)

    end_graph = False
    fields = []
    graphs = []

    for row in input_field_list:

        if len(row[2]) > 1:
            if end_graph:
                graphs.append([meta, meta_name, group, group_name, fields])

            # Start a new graph
            meta = row[0]
            meta_name = row[1]
            group = row[2]
            group_name = row[3]
            fields = [row[4]]
            end_graph = True

        else:
            fields.append(row[4])

    # Add final row
    graphs.append([meta, meta_name, group, group_name, fields])

    return graphs


def unique_values(table, field):

    # Adapted from https://gis.stackexchange.com/questions/208430/trying-to-extract-a-list-of-unique-values-from-a-field-using-python
    with arcpy.da.SearchCursor(table, [field]) as cursor:
        return sorted({row[0] for row in cursor})


if __name__ == "__main__":
    main()
