import arcpy
import os
from PNET_Functions import make_folder, remove_folder, get_folder_list, \
    finish, attribute_table_to_list, get_field_index, delete_temps

# -------------------------------------------------------------------------------
# Name:        PNET Step 1
# Purpose:     Prepares Data for Snapping, Creates Folder Structure
#
# Author:      Tyler Hatch
#
# Created:     09/26/2019
# Latest Update: 5/4/2020
# -------------------------------------------------------------------------------

# A shapefile containing all relevant watersheds boundaries (And No More)
watersheds = arcpy.GetParameterAsText(0)
# A shapefile containing all TOR points
tor_points = arcpy.GetParameterAsText(1)
# A shapefile containing all BOR points
bor_points = arcpy.GetParameterAsText(2)
# The stream network to be used for the entirety of the tool
stream_network = arcpy.GetParameterAsText(3)
# A Folder where you want the main structure of this project to be created
root_folder = arcpy.GetParameterAsText(4)
# Data year (The year which you want field data to be closest to)
data_year = int(arcpy.GetParameterAsText(5))


def main():

    # Initialize Variables
    arcpy.env.overwriteOutput = True
    watershed_list = []
    to_merge_tor = []
    to_merge_bor = []
    to_merge_network = []
    temps_to_delete = []
    watershed_layer = "Watershed"
    arcpy.MakeFeatureLayer_management(watersheds, watershed_layer)

    # Remove all existing content
    for folder in get_folder_list(root_folder, True):
        remove_folder(folder)

    # Get the name of every watershed
    # TODO make more general
    for row in arcpy.da.SearchCursor(watersheds, ["Name"]):

        watershed_list.append(row[0])

    # This loops for each watershed
    for watershed in watershed_list:

        arcpy.AddMessage("Starting " + watershed + "...")

        # Create folder structure within root folder for this watershed
        watershed_folder = make_structure(root_folder, watershed)

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
        year_dif_field = create_year_distance(tor_temp_location, "yr", data_year)
        delete_identical(tor_temp_location, "SiteID", year_dif_field, "RchID", tor_save_location)
        to_merge_tor.append(tor_save_location)

        # Clip the BOR points to this watershed and save them
        bor_save_location = os.path.join(watershed_folder, "Inputs", "Points", "BOR_Points.shp")
        bor_temp_location = os.path.join(watershed_folder, "Inputs", "Points", "BOR_Points_Temp.shp")
        temps_to_delete.append(bor_temp_location)
        arcpy.Clip_analysis(bor_points, clipped_watershed, bor_temp_location)

        # Only save one point per reach and site
        create_year_distance(bor_temp_location, "yr")
        delete_identical(bor_temp_location, "SiteID", year_dif_field, "RchID", bor_save_location)
        to_merge_bor.append(bor_save_location)

        # Clip the stream_network to this watershed and save it
        stream_save_location = os.path.join(watershed_folder, "Inputs", "Stream_Network", "Stream_Network.shp")
        arcpy.Clip_analysis(stream_network, clipped_watershed, stream_save_location)
        # TODO make more general
        to_merge_network.append(stream_save_location)

    arcpy.AddMessage("Starting Project Wide...")

    # Make a folder to contain Project Wide outputs and inputs
    project_folder = make_structure(root_folder, "00_ProjectWide")

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
    stream_save_location = os.path.join(project_folder, "Inputs", "Stream_Network", "Stream_Network.shp")
    arcpy.Copy_management(stream_network, stream_save_location)

    arcpy.AddMessage("\t Saving Watersheds...")
    # Take Watershed Boundaries, and save it to the ProjectWide folder
    wat_save_location = os.path.join(project_folder, "Inputs", "Watershed_Boundary", "Watershed_Boundary.shp")
    arcpy.Copy_management(watersheds, wat_save_location)

    delete_temps(temps_to_delete)

    finish()


def make_structure(main_folder, watershed_name):

    # Make sure there are no strange characters in the Watershed's name
    watershed_name = watershed_name.replace(" ", "")
    watershed_name = watershed_name.replace("-", "")

    # Create a folder within the main folder with the Watershed's name
    watershed_folder = make_folder(main_folder, watershed_name)

    # Within the Watershed folder, create a folder for inputs, intermediates, and outputs
    input_folder = make_folder(watershed_folder, "Inputs")
    intermediate_folder = make_folder(watershed_folder, "Intermediates")
    output_folder = make_folder(watershed_folder, "Outputs")

    # Make all folders within inputs
    make_folder(input_folder, "Watershed_Boundary")
    make_folder(input_folder, "Stream_Network")
    make_folder(input_folder, "Data_Networks")
    make_folder(input_folder, "Database")

    point_folder = make_folder(input_folder, "Points")

    # Make all folders within intermediates
    point_folder_int = make_folder(intermediate_folder, "Points")
    make_folder(point_folder_int, "Unsnapped")
    make_folder(point_folder_int, "Snapped")
    make_folder(point_folder_int, "Unsnapped_Fixed")

    me_folder = make_folder(intermediate_folder, "Reach_Editing")
    make_folder(me_folder, "Inputs")
    make_folder(me_folder, "Outputs")

    ext_folder = make_folder(intermediate_folder, "Extraction")
    make_folder(ext_folder, "Inputs")
    make_folder(ext_folder, "Outputs")

    # Make all folders within outputs
    make_folder(output_folder, "Extracted_Data")
    make_folder(output_folder, "Comparisons")

    return watershed_folder


def create_year_distance(shapefile, year_field, data_year):
    # Creates a field showing how far away (timewise) the reach is from our target year
    new_field = "Year_Dif"
    arcpy.AddField_management(shapefile, new_field, "SHORT")
    arcpy.CalculateField_management(shapefile, new_field, "abs({} - !{}!)".format(data_year, year_field),"PYTHON_9.3", "")
    return new_field


def delete_identical(shapefile, group_field, year_dif_field, id_field, final_save):

    data_list = attribute_table_to_list(shapefile)
    group_index = get_field_index(group_field, shapefile)
    year_index = get_field_index(year_dif_field, shapefile)
    id_index = get_field_index(id_field, shapefile)

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

if __name__ == "__main__":
    main()
