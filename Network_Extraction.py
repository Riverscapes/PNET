import arcpy
import os
from collections import Counter
import PNET_Functions

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

    watershed_folders = get_watershed_folders(root_folder)
    projectwide_output = os.path.join(root_folder, "00_ProjectWide", "Intermediates", "Extraction", "Outputs")
    delete_old(projectwide_output)

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
            if not is_empty(data_network):

                old_reaches = os.path.join(watershed_folder, "Intermediates",
                                           "Extraction", "Inputs", "Field_Reaches_Clean.shp")

                # Create a name for this data network so it can have a unique save location
                data_network_name = data_network.replace(os.path.join(watershed_folder, "Inputs", "Data_Networks"), "")
                data_network_name = data_network_name.replace(".shp", "")
                data_network_name = data_network_name.replace("\\", "")

                arcpy.AddMessage("\tStarting {}...".format(data_network_name))

                data_network_folder = make_folder(output_folder, data_network_name)
                delete_old(data_network_folder)

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

                data_network_fields = get_fields(data_network)
                pnet_fields = get_fields(old_reaches)
                fields_to_keep = pnet_fields + data_network_fields



                # Extracts data from the data network to PIBO reaches using a weighted average system.
                extract_network(reaches, clipped_data_network, reaches_save, data_network_folder, pnet_fields)

                # Remove all unnecessary fields
                keep_fields(reaches_save, fields_to_keep)
                #remove_empty_fields(reaches_save, pnet_fields)

                # Delete any temporary shape files created
                delete_temps(to_delete)



                create_csv(os.path.join(data_network_folder, "{}.csv".format(data_network_name)), reaches_save)
                to_merge[data_network_count].append([reaches_save, data_network_name])

    # Iterate through to_merge, and save a point and network shapefile for each data network

    arcpy.AddMessage("Saving Projectwide...")
    for data_network_type in to_merge:
        to_merge_networks = []
        save_name = data_network_type[0][1]
        save_folder = make_folder(projectwide_output, save_name)
        for watershed in data_network_type:
            to_merge_networks.append(watershed[0])
        csv_save = arcpy.Merge_management(to_merge_networks,
                               os.path.join(save_folder, save_name + "_Points_Extracted.shp"))
        create_csv(os.path.join(save_folder, "{}.csv".format(save_name)), csv_save)

    finish()


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
    delete_temps(to_delete)

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
    keep_fields(network, fields_to_keep)

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


if __name__ == "__main__":
    main()
