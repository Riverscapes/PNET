import arcpy
import os
import PNET_Functions as pnet
import time

# -------------------------------------------------------------------------------
# Name:        PNET Step 1
# Purpose:     Prepares Data for Snapping, Creates Folder Structure
#
# Author:      Tyler Hatch
#
# Created:     09/26/2019
# Latest Update: 2/9/2020
# -------------------------------------------------------------------------------

# A Folder where you want the main structure of this project to be created
root_folder = arcpy.GetParameterAsText(0)
# A shapefile containing all relevant watersheds boundaries (And No More)
watersheds = arcpy.GetParameterAsText(1)
# A shapefile containing all TOR points
tor_points = arcpy.GetParameterAsText(2)
# A shapefile containing all BOR points
bor_points = arcpy.GetParameterAsText(3)
# The stream network to be used for the entirety of the tool
stream_network = arcpy.GetParameterAsText(4)
# Data year (The year which you want field data to be closest to)
data_year = int(arcpy.GetParameterAsText(5))
# Set this to true if you want the threshold value to be used. This should almost always be True
use_threshold = pnet.parse_bool(arcpy.GetParameterAsText(6))
# The longest distance (m) to go before snapping stops and remaining points are considered outliers to be investigated
threshold_range = int(arcpy.GetParameterAsText(7))
# Snapping distances will increase by this increment (m). Default is ten. Lower values mean longer run time.
custom_increment = 10


def main():

    # Blank lists to hold data later
    watershed_list, \
        to_merge_tor, \
        to_merge_bor, \
        to_merge_network,\
        temps_to_delete, \
        saved_tor_points_snapped, \
        saved_bor_points_snapped, \
        saved_tor_points_unsnapped, \
        saved_bor_points_unsnapped = [], [], [], [], [], [], [], [], []

    # Create a layer so that selections can happen
    watershed_layer = "Watershed"
    arcpy.MakeFeatureLayer_management(watersheds, watershed_layer)

    # Remove all existing content
    for folder in pnet.get_folder_list(root_folder, True):
        pnet.remove_folder(folder)

    # Delete old content from this tool being re run.
    pnet.delete_old(os.path.join(root_folder, "00_ProjectWide", "Intermediates", "Points", "Snapped"))
    pnet.delete_old(os.path.join(root_folder, "00_ProjectWide", "Intermediates", "Points", "Unsnapped"))

    # Get the name of every watershed
    for row in arcpy.da.SearchCursor(watersheds, ["Name"]):
        watershed_list.append(row[0])

    start_time = pnet.start()

    # This loops for each watershed
    for watershed in watershed_list:

        pnet.update(watershed, watershed_list, start_time)

        # Create folder structure within root folder for this watershed
        watershed_folder = make_structure(root_folder, watershed)

        # Prepare data in this watershed (Snapping, Choosing Reaches, etc.)
        tor, bor, network = watershed_data_prep(watershed, watershed_folder, watershed_layer)

        # Add data in lists to be merged later
        to_merge_tor.append(tor)
        to_merge_bor.append(bor)
        to_merge_network.append(network)

        tor, bor, tor_u, bor_u = watershed_point_snapping(watershed_folder)

        saved_tor_points_snapped.append(tor)
        saved_bor_points_snapped.append(bor)
        saved_tor_points_unsnapped.append(tor_u)
        saved_bor_points_unsnapped.append(bor_u)

    pnet.update_pw()

    # Make a folder to contain Project Wide outputs and inputs
    project_folder = make_structure(root_folder, "00_ProjectWide")

    projectwide_data_prep(project_folder, to_merge_tor, to_merge_bor, to_merge_network)

    projectwide_point_snapping(project_folder, saved_tor_points_snapped, saved_bor_points_snapped,
                               saved_bor_points_unsnapped, saved_tor_points_unsnapped)

    pnet.delete_temps(temps_to_delete)

    pnet.finish()


def make_structure(main_folder, watershed_name):

    # Make sure there are no strange characters in the Watershed's name
    watershed_name = watershed_name.replace(" ", "")
    watershed_name = watershed_name.replace("-", "")

    # Create a folder within the main folder with the Watershed's name
    watershed_folder = pnet.make_folder(main_folder, watershed_name)

    # Within the Watershed folder, create a folder for inputs, intermediates, and outputs
    input_folder = pnet.make_folder(watershed_folder, "Inputs")
    intermediate_folder = pnet.make_folder(watershed_folder, "Intermediates")
    output_folder = pnet.make_folder(watershed_folder, "Outputs")

    # Make all folders within inputs
    pnet.make_folder(input_folder, "Watershed_Boundary")
    pnet.make_folder(input_folder, "Stream_Network")
    pnet.make_folder(input_folder, "Data_Networks")
    pnet.make_folder(input_folder, "Database")

    point_folder = pnet.make_folder(input_folder, "Points")

    # Make all folders within intermediates
    point_folder_int = pnet.make_folder(intermediate_folder, "Points")
    pnet.make_folder(point_folder_int, "Unsnapped")
    pnet.make_folder(point_folder_int, "Snapped")
    pnet.make_folder(point_folder_int, "Unsnapped_Fixed")

    me_folder = pnet.make_folder(intermediate_folder, "Reach_Editing")
    pnet.make_folder(me_folder, "Inputs")
    pnet.make_folder(me_folder, "Outputs")

    ext_folder = pnet.make_folder(intermediate_folder, "Extraction")
    pnet.make_folder(ext_folder, "Inputs")
    pnet.make_folder(ext_folder, "Outputs")

    # Make all folders within outputs
    pnet.make_folder(output_folder, "Extracted_Data")
    pnet.make_folder(output_folder, "Comparisons")

    return watershed_folder


def create_year_distance(shapefile, year_field):
    # Creates a field showing how far away (timewise) the reach is from our target year
    new_field = "Year_Dif"
    arcpy.AddField_management(shapefile, new_field, "SHORT")
    arcpy.CalculateField_management(shapefile, new_field, "abs(2016 - !{}!)".format(year_field),"PYTHON_9.3", "")
    return new_field


def delete_identical(shapefile, group_field, year_dif_field, id_field, final_save):

    data_list = pnet.attribute_table_to_list(shapefile)
    group_index = pnet.get_field_index(group_field, shapefile)
    year_index = pnet.get_field_index(year_dif_field, shapefile)
    id_index = pnet.get_field_index(id_field, shapefile)

    # Create a dictionary with entries for each group
    site_dictionary = {}

    for row in data_list:
        if row[group_index] not in site_dictionary:
            site_dictionary[row[group_index]] = []
        site_dictionary[row[group_index]].append(row[1:])

    # A list of all reach IDs that need to be kept
    keep_reaches = []

    # Look at every site
    for site in site_dictionary:
        # Create a list of all the different year differences
        year_difs = []
        for reach in site_dictionary[site]:
            year_difs.append(reach[year_index-1])

        # Find which reach has the smallest year difference in the site
        minimum = min(year_difs)
        for reach in site_dictionary[site]:
            if reach[year_index-1] == minimum:
                keep_reach = reach[id_index-1]
        keep_reaches.append(keep_reach)

    # Create a layer to select from
    select_layer = "Reaches"
    arcpy.MakeFeatureLayer_management(shapefile, select_layer)

    # Select all of the reaches we want to keep then invert the selection
    for good_reach in keep_reaches:
        arcpy.SelectLayerByAttribute_management(select_layer, 'ADD_TO_SELECTION',
                                                '{} = {}'.format(id_field, good_reach))

    arcpy.CopyFeatures_management(select_layer, final_save)


def watershed_data_prep(watershed, watershed_folder, watershed_layer):

    temps_to_delete = []
    # Get the boundary of this watershed
    query = 'NAME = \'' + watershed + '\''

    arcpy.SelectLayerByAttribute_management(watershed_layer, 'NEW_SELECTION', query)
    clipped_watershed = os.path.join(watershed_folder, "Inputs", "Watershed_Boundary", "Watershed_Boundary.shp")
    arcpy.CopyFeatures_management(watershed_layer, clipped_watershed)
    arcpy.SelectLayerByAttribute_management(watershed_layer, "CLEAR_SELECTION")

    # Clip the TOR points to this watershed and save them
    tor_save_location = os.path.join(watershed_folder, "Inputs", "Points", "TOR_Points.shp")
    tor_temp_location = os.path.join(watershed_folder, "Inputs", "Points", "TOR_Points_Temp.shp")
    temps_to_delete.append(tor_temp_location)
    arcpy.Clip_analysis(tor_points, clipped_watershed, tor_temp_location)

    # Only save one point per reach and site
    year_dif_field = create_year_distance(tor_temp_location, "yr")
    delete_identical(tor_temp_location, "SiteID", year_dif_field, "RchID", tor_save_location)

    # Clip the BOR points to this watershed and save them
    bor_save_location = os.path.join(watershed_folder, "Inputs", "Points", "BOR_Points.shp")
    bor_temp_location = os.path.join(watershed_folder, "Inputs", "Points", "BOR_Points_Temp.shp")
    temps_to_delete.append(bor_temp_location)
    arcpy.Clip_analysis(bor_points, clipped_watershed, bor_temp_location)

    # Only save one point per reach and site
    create_year_distance(bor_temp_location, "yr")
    delete_identical(bor_temp_location, "SiteID", year_dif_field, "RchID", bor_save_location)

    # Clip the stream_network to this watershed and save it
    stream_save_location = os.path.join(watershed_folder, "Inputs", "Stream_Network", "Stream_Network.shp")
    arcpy.Clip_analysis(stream_network, clipped_watershed, stream_save_location)

    pnet.delete_temps(temps_to_delete)

    return tor_save_location, bor_save_location, stream_save_location


def projectwide_data_prep(project_folder, to_merge_tor, to_merge_bor, to_merge_network):

    arcpy.AddMessage("\t Saving TOR Points...")
    # Merge every Watershed's TOR points, and save it to the ProjectWide folder
    tor_save_location = os.path.join(project_folder, "Inputs", "Points", "TOR_Points.shp")
    arcpy.Merge_management(to_merge_tor, tor_save_location)

    arcpy.AddMessage("\t Saving BOR Points...")
    # Merge every Watershed's BOR points, and save it to the ProjectWide folder
    bor_save_location = os.path.join(project_folder, "Inputs", "Points", "BOR_Points.shp")
    arcpy.Merge_management(to_merge_bor, bor_save_location)

    arcpy.AddMessage("\t Saving Stream Network...")

    # Take Stream Network, and save it to the ProjectWide folder
    network_save_location = os.path.join(project_folder, "Inputs", "Stream_Network", "Stream_Network.shp")
    arcpy.Merge_management(to_merge_network, network_save_location)

    arcpy.AddMessage("\t Saving Watersheds...")
    # Take Watershed Boundaries, and save it to the ProjectWide folder
    wat_save_location = os.path.join(project_folder, "Inputs", "Watershed_Boundary", "Watershed_Boundary.shp")
    arcpy.Copy_management(watersheds, wat_save_location)


def watershed_point_snapping(watershed_folder):

    # Get all file names
    output_folder = os.path.join(watershed_folder, "Intermediates", "Points")
    network = os.path.join(watershed_folder, "Inputs", "Stream_Network", "Stream_Network.shp")

    pnet.delete_old(os.path.join(output_folder, "Snapped"))
    pnet.delete_old(os.path.join(output_folder, "Unsnapped"))

    bor_points_old = os.path.join(watershed_folder, "Inputs", "Points", "BOR_Points.shp")
    tor_points_old = os.path.join(watershed_folder, "Inputs", "Points", "TOR_Points.shp")

    bor_points_new_temp = os.path.join(output_folder, "BOR_Points_Temp.shp")
    tor_points_new_temp = os.path.join(output_folder, "TOR_Points_Temp.shp")

    bor_points_new_snapped = os.path.join(output_folder, "Snapped", "BOR_Points_Snapped.shp")
    tor_points_new_snapped = os.path.join(output_folder, "Snapped", "TOR_Points_Snapped.shp")

    bor_points_new_unsnapped = os.path.join(output_folder, "Unsnapped", "BOR_Points_Unsnapped.shp")
    tor_points_new_unsnapped = os.path.join(output_folder, "Unsnapped", "TOR_Points_Unsnapped.shp")

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

    pnet.delete_temps([bor_points_new_temp, tor_points_new_temp])

    return tor_points_new_snapped, bor_points_new_snapped, tor_points_new_unsnapped, bor_points_new_unsnapped


def projectwide_point_snapping(project_folder, tor, bor, tor_u, bor_u):

    output_folder = os.path.join(project_folder, "Intermediates", "Points")

    bor_points_new_snapped = os.path.join(output_folder, "Snapped", "BOR_Points_Snapped.shp")
    tor_points_new_snapped = os.path.join(output_folder, "Snapped", "TOR_Points_Snapped.shp")
    bor_points_new_unsnapped = os.path.join(output_folder, "Unsnapped", "BOR_Points_Unsnapped.shp")
    tor_points_new_unsnapped = os.path.join(output_folder, "Unsnapped", "TOR_Points_Unsnapped.shp")

    arcpy.AddMessage("\t Saving Snapped Points...")
    arcpy.Merge_management(bor, bor_points_new_snapped)
    arcpy.Merge_management(tor, tor_points_new_snapped)

    arcpy.AddMessage("\t Saving Unsnapped Points...")
    arcpy.Merge_management(bor_u, bor_points_new_unsnapped)
    arcpy.Merge_management(tor_u, tor_points_new_unsnapped)

    arcpy.AddMessage("\t Saving Points to Fix...")
    arcpy.Copy_management(bor_points_new_unsnapped, os.path.join(output_folder, "Unsnapped_Fixed", "To_Fix_BOR.shp"))
    arcpy.Copy_management(tor_points_new_unsnapped, os.path.join(output_folder, "Unsnapped_Fixed", "To_Fix_TOR.shp"))


if __name__ == "__main__":
    main()
