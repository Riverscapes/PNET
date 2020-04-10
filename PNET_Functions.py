import arcpy
import os
import shutil
import csv

# -------------------------------------------------------------------------------
# Name:        PNET_Functions
# Purpose:     A collection of functions used in multiple scripts across PNET
#
# Author:      Tyler Hatch
#
# Created:     2/9/2020
# Latest Update: 2/9/2020
# -------------------------------------------------------------------------------


def parse_bool(parameter):
    return parameter == 'true'


def parse_multistring(parameter):
    return parameter.split(";")


def make_folder(path_to_location, new_folder_name):

    # Create a new folder of a given name, as long as it doesn't already exist
    new_folder = os.path.join(path_to_location, new_folder_name)
    if not os.path.exists(new_folder):
        os.mkdir(new_folder)
    return new_folder


def delete_old(folder_to_clear):
    # Clears an individual folder of all its data
    if os.path.exists(folder_to_clear):

        folder = folder_to_clear
        for the_file in os.listdir(folder):
            file_path = os.path.join(folder, the_file)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
            except Exception as e:
                print(e)


def delete_temps(temps_to_delete):
    if True:
        for temp_file in temps_to_delete:
            arcpy.Delete_management(temp_file)


def remove_folder(folder_to_clear):
    if os.path.exists(folder_to_clear):
        shutil.rmtree(folder_to_clear)


def is_even(number):
    # Checks if a number is even
    return (number % 2) == 0


def get_folder_list(main_folder, include_project):

    os.chdir(main_folder)

    # List all folders in parent folder path - note this is not recursive
    dir_list = filter(lambda x: os.path.isdir(x), os.listdir('.'))

    # Remove folders in the list that start with '00_' since these aren't our huc8 folders
    if not include_project:
        for dir in dir_list[:]:
            if dir.startswith('00_'):
                dir_list.remove(dir)

    else:
        for dir in dir_list[:]:
            if dir.startswith('00_') and not dir.startswith('00_ProjectWide'):
                dir_list.remove(dir)

    return dir_list


def is_empty(shapefile):
    return arcpy.GetCount_management(shapefile)[0] == "0"


def get_watershed_folders(main_folder):

    to_return = []
    for watershed in get_folder_list(main_folder, False):
        to_return.append(os.path.join(main_folder, watershed))
    return to_return


def remove_fields(fields_to_delete, shapefile):
    field_names = [f.name for f in arcpy.ListFields(shapefile)]
    for field in fields_to_delete:
        if field in field_names:
            arcpy.DeleteField_management(shapefile, field)


def attribute_table_to_list(shapefile):
    field_names = [f.name for f in arcpy.ListFields(shapefile)]
    to_return = []

    # Turns the shapefile from before into a Python list. This is to minimize interaction with cursors.
    for row in arcpy.da.SearchCursor(shapefile, field_names):
        to_add = []
        for count, field in enumerate(field_names):
            to_add.append(row[count])
        to_return.append(to_add)

    return to_return


def get_field_index(field, shapefile):

    field_names = [f.name for f in arcpy.ListFields(shapefile)]
    if field in field_names:
        return field_names.index(field)
    else:
        return False


def create_csv(output_csv, input_table):

    # Adapted from https://community.esri.com/thread/167462, Blake Terhune

    fields = [f.name for f in arcpy.ListFields(input_table)]
    with open(output_csv, "w") as csvfile:
        csvwriter = csv.writer(csvfile, delimiter=',', lineterminator='\n')
        # Write field name header line
        csvwriter.writerow(fields)
        # Write data rows
        with arcpy.da.SearchCursor(input_table, fields) as s_cursor:
            for row in s_cursor:
                csvwriter.writerow(row)
    return output_csv


def write_to_file(file_to_write, text):

    file = open(file_to_write, "a+")
    file.write("\n")
    file.write(text)
    file.close()


def read_file(file_to_read, line, do_split):

    file = open(file_to_read, "r")
    return_list = file.readlines()
    file.close()
    if do_split:
        to_split = return_list[line + 1].replace("\n", "")
        return split_line(to_split)
    else:
        return return_list[line+1].replace("\n", "")


def get_parameters_file(root_folder):
    return os.path.join(root_folder, "00_ProjectWide", "Inputs", "Parameters", "Parameters.txt")


def split_line(line_to_split):
    return line_to_split.split(r"/")


def create_split_line(list):

    to_return = ""

    for item in list:
        joined = to_return.join([to_return+item+"/"])
        to_return = joined

    return to_return[:-1]


def write_fields_to_text(text_file, shapefile):

    fields = get_fields(shapefile)
    split_fields = create_split_line(fields)
    write_to_file(text_file, split_fields)


def get_fields(shapefile):
    return [f.name for f in arcpy.ListFields(shapefile)]


def keep_fields(shapefile, fields_to_keep):
    field_names = [f.name for f in arcpy.ListFields(shapefile)]
    delete_fields = []
    for field in field_names:
        if field not in fields_to_keep:
            delete_fields.append(field)

    arcpy.DeleteField_management(shapefile, delete_fields)


def remove_empty_fields(shapefile, exceptions=["TempField"]):

    field_names = [f.name for f in arcpy.ListFields(shapefile)]
    bad_fields = []
    for exception in exceptions:
        if exception in field_names:
            field_names.remove(exception)
    for field in field_names:
        with arcpy.da.SearchCursor(shapefile, field) as cursor:
            this_field = []
            for row in cursor:
                this_field.append(row[0])
            if len(set(this_field)) == 1:
                bad_fields.append(field)
    for bad_field in bad_fields:
        if bad_field in get_fields(shapefile):
            arcpy.DeleteField_management(shapefile, bad_field)
    return bad_fields


def csv_to_list(csv_to_read):
    data = []
    with open(csv_to_read, 'r') as f:
        reader = csv.reader(f, delimiter=',')
        for line in reader:
            data.append(line)

    return data


def finish():
    print "\n---Finished!---"
