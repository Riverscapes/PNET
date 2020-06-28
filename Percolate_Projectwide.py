import arcpy
import os
from PNET_Functions import get_watershed_folders, delete_old, finish, get_folder_list, \
    is_empty, write_fields_to_text, parse_multistring

# The folder where a PNET Run has already been made
root_folder = r'C:\Users\Tyler\Desktop\Work\FullRun'

def main():

    # Initialize variables and file locations
    arcpy.env.overwriteOutput = True

    watershed_folders = get_watershed_folders(root_folder)
    projectwide = os.path.join(root_folder, "00_ProjectWide", "Outputs", "Extracted_Data", "Extraction_Merge_Points.shp")

    for watershed in watershed_folders:

        arcpy.AddMessage("\tStarting " + watershed + "...")

        boundary = os.path.join(watershed, "Inputs", "Watershed_Boundary", "Watershed_Boundary.shp")

        # Clip the current data network to this watershed
        out_folder = os.path.join(watershed, "Outputs", "Extracted_Data")
        delete_old(out_folder)
        new_save_location = os.path.join(out_folder, "Extraction_Merge_Points.shp")
        arcpy.Clip_analysis(projectwide, boundary, new_save_location)


if __name__ == "__main__":
    main()
