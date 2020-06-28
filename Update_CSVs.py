import arcpy
import os
from PNET_Functions import get_watershed_folders, delete_old, finish, get_folder_list, is_empty, create_csv, get_fields

# The folder containing all watershed folders
root_folder = r'C:\Users\Tyler\Desktop\Work\FullRun'


def main():

    # Initialize variables and file locations
    arcpy.env.overwriteOutput = True

    watershed_folders = get_watershed_folders(root_folder)
    projectwide_output = os.path.join(root_folder, "00_ProjectWide")
    watershed_folders.append(projectwide_output)

    for watershed in watershed_folders:

        arcpy.AddMessage("Working on {}...".format(watershed))
        output_folder = os.path.join(watershed, "Outputs", "Extracted_Data")
        data = os.path.join(output_folder, "Extraction_Merge_Points.shp")
        create_csv(os.path.join(output_folder, "All_Data.csv"), data)


if __name__ == "__main__":
    main()
