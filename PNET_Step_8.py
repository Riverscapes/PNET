import arcpy
import os
from PNET_Functions import get_watershed_folders, delete_old, finish, get_folder_list, is_empty, create_csv, get_fields

# -------------------------------------------------------------------------------
# Name:        PNET Step 8
# Purpose:     Collects all extracted reaches and merges them into one shapefile. Cleans up unnecessary fields.
#
# Author:      Tyler Hatch
#
# Created:     10/24/2019
# Latest Update: 1/22/2020
# -------------------------------------------------------------------------------

# The folder containing all watershed folders
root_folder = arcpy.GetParameterAsText(0)

def main():
    # Initialize variables and file locations
    arcpy.env.overwriteOutput = True

    watershed_folders = get_watershed_folders(root_folder)
    projectwide_output = os.path.join(root_folder, "00_ProjectWide", "Outputs", "Extracted_Data")
    delete_old(projectwide_output)
    to_merge_points = []
    req_fields = ["RchID", "FID", "Shape"]

    # This loops for each watershed folder
    for watershed in watershed_folders:
        arcpy.AddMessage("Working on {}...".format(watershed))

        # Initialize list of all unique data networks within this watershed
        point_list = get_data_points(watershed)
        output_folder = os.path.join(watershed, "Outputs", "Extracted_Data")
        delete_old(output_folder)

        # Create temporary shapefiles to store spatially joined data
        all_joined = os.path.join(output_folder, "temp.shp")

        # Join the first and second network's data together, and store them into a temporary shapefile
        arcpy.AddMessage("\t Merging first points...")

        arcpy.Copy_management(point_list[0], all_joined)
        all_fields = get_fields(all_joined)
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
                all_fields = get_fields(all_joined)
                for field in req_fields:
                    if field in all_fields:
                        all_fields.remove(field)

        # Save the output into the correct folder
        save = arcpy.Copy_management(all_joined,
                                     os.path.join(output_folder, "Extraction_Merge_Points.shp"))

        to_merge_points.append(save)

        create_csv(os.path.join(output_folder, "All_Data.csv"), save)

        # Delete both temp shapefiles
        arcpy.Delete_management(all_joined)
        arcpy.Delete_management(data_temp)

    arcpy.AddMessage("Working on Projectwide...")

    make_csv = arcpy.Merge_management(to_merge_points,
                           os.path.join(projectwide_output, "Extraction_Merge_Points.shp"))
    create_csv(os.path.join(projectwide_output, "All_Data.csv"), make_csv)
    finish()


def get_data_points(watershed_folder):

    # Gets a list of all network shapefile locations
    to_return = []
    network_folder = os.path.join(watershed_folder, "Intermediates", "Extraction", "Outputs")
    data_network_list = get_folder_list(network_folder, False)

    for folder in data_network_list:

        for r, d, f in os.walk(folder):
            for file in f:
                # This line makes sure it is a shapefile
                if '.shp' in file and 'Reaches' not in file and '.xml' not in file and '.lock' not in file:
                    to_return.append(os.path.join(r, file))
    to_keep = []
    for file in to_return:
        if not is_empty(file):
            to_keep.append(file)

    return to_keep


def remove_existing_fields(all_fields_list, shapefile):

    # Removes all fields tht are already part of the merged shapefile
    cur_fields = get_fields(shapefile)
    deleted_fields = []
    for cur_field in cur_fields:
        if cur_field in all_fields_list:
            arcpy.DeleteField_management(shapefile, cur_field)
            deleted_fields.append(cur_field)

    return deleted_fields


if __name__ == "__main__":
    main()
