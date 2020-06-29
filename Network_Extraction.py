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


def main():

    reach_preparation(root_folder, fixed_points)
    reach_editing(root_folder)
    data_cleaning(root_folder)


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


if __name__ == "__main__":
    main()
