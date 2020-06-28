import arcpy
import os
from PNET_Functions import get_watershed_folders, delete_old, finish, get_folder_list, \
    is_empty, write_fields_to_text, parse_multistring
# -------------------------------------------------------------------------------
# Name:        PNET Step 6
# Purpose:     Takes as many different full runs as needed and puts them in a folder's structure
#
# Author:      Tyler Hatch
#
# Created:     1/20/2020
# Latest Update: 1/22/2020
# -------------------------------------------------------------------------------

# The folder where a PNET Run has already been made
root_folder = arcpy.GetParameterAsText(0)
# A list of links to shapefiles that contain entire model runs
data_networks_list_in = parse_multistring(arcpy.GetParameterAsText(1))


def main():

    # Initialize variables and file locations
    arcpy.env.overwriteOutput = True

    watershed_folders = get_watershed_folders(root_folder)
    projectwide_output = os.path.join(root_folder, "00_ProjectWide", "Inputs", "Data_Networks")
    projectwide_network = os.path.join(root_folder, "00_ProjectWide",  "Inputs", "Stream_Network", "Stream_Network.shp")
    delete_old(projectwide_output)
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
        delete_old(os.path.join(watershed, "Inputs", "Data_Networks"))

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
            if is_empty(new_network_save):
                arcpy.AddMessage("Did not save {}, as it was empty".format(new_network_save))
                arcpy.Delete_management(new_network_save)

        arcpy.AddMessage("\tSaving Projectwide...")
        new_network_save = os.path.join(projectwide_output, name)
        arcpy.Clip_analysis(network, projectwide_network, new_network_save)

    finish()


if __name__ == "__main__":
    main()
