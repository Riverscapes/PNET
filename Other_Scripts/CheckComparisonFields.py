import arcpy
import os
from PNET_Functions import get_watershed_folders, delete_old, create_csv,\
    get_fields, csv_to_list, parse_multistring, make_folder


# -------------------------------------------------------------------------------
# Name:        PNET Step 9
# Purpose:     Creates Comparison Fields
# Author:      Tyler Hatch
#
# Created:     3/1/2020
# Latest Update: 3/1/2020
# -------------------------------------------------------------------------------

# The folder containing all watershed folders
root_folder = r''
# The csv containing all field aquired data
field_db = r''
# CSV to set field data from
input_field_csv = r''



def main():
    # Initialize variables and file locations
    arcpy.env.overwriteOutput = True

    # Setup projectwide data
    projectwide_input = os.path.join(root_folder, "00_ProjectWide", "Outputs", "Extracted_Data", "All_Data.csv")

    # Set the field lists to the values from the fields value
    pnet_fields, field_db_fields, new_fields_initial = read_field_csv(input_field_csv)

    exist_fields = get_fields(projectwide_input)

    for field in set(pnet_fields):
        if field not in exist_fields and field is not "":
            print("[{}] PNET field is missing from {}".format(field, projectwide_input))

    exist_fields = get_fields(field_db)

    for field in set(field_db_fields):
        if field not in exist_fields and field is not "":
            print("[{}] Field collected field is missing from {}".format(field, field_db))


def save_db(database, main_folder):
    save_loc = os.path.join(main_folder, "Inputs", "Database", "Field_Database.csv")
    shutil.copyfile(database, save_loc)
    return save_loc


def is_csv(file):
    return file.endswith('.csv')


def read_field_csv(file):

    input_field_list = csv_to_list(file)

    # remove headers
    input_field_list.pop(0)

    list_a, list_b, list_c = [], [], []

    for unique_field in input_field_list:
        list_a.append(unique_field[0])
        list_b.append(unique_field[1])
        list_c.append(unique_field[2])

    return list_a, list_b, list_c


if __name__ == "__main__":
    main()
