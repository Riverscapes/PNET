import arcpy
import os
from collections import Counter
import PNET_Functions

# -------------------------------------------------------------------------------
# Name:        PNET Step 4
# Purpose:     Edits stream segments and points to create field reaches and points
# Author:      Tyler Hatch
#
# Created:     09/23/2019
# Latest Update: 1/22/2020
# -------------------------------------------------------------------------------


# The folder containing all watershed folders
root_folder = arcpy.GetParameterAsText(0)


def main():

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


if __name__ == "__main__":
    main()
