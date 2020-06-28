import arcpy
import os
import shutil
from PNET_Functions import get_watershed_folders, delete_old, create_csv,\
    get_fields, csv_to_list, parse_multistring, make_folder
import scipy.stats as stat
import numpy as np
import matplotlib.pyplot as plt
import math

# -------------------------------------------------------------------------------
# Name:        PNET Step 9
# Purpose:     Creates Comparison Fields
# Author:      Tyler Hatch
#
# Created:     3/1/2020
# Latest Update: 3/1/2020
# -------------------------------------------------------------------------------

# The folder containing all watershed folders
root_folder = arcpy.GetParameterAsText(0)
# The database containing all field data
field_db = arcpy.GetParameterAsText(1)

# Fields from PNET that we want to compare (must be in same order as field database fields)
pnet_fields = parse_multistring(arcpy.GetParameterAsText(2))
# Fields from the field that we want to compare (must be in same order as PNET fields)
field_db_fields = parse_multistring(arcpy.GetParameterAsText(3))
# What you want the new names of the fields to be when comparing
new_fields_initial = parse_multistring(arcpy.GetParameterAsText(4))
# CSV to set field data from instead (optional, expects headers)
input_field_csv = arcpy.GetParameterAsText(5)


def main():
    # Initialize variables and file locations
    arcpy.env.overwriteOutput = True
    watershed_folders = get_watershed_folders(root_folder)

    # Setup projectwide data

    projectwide_output = make_folder(os.path.join(root_folder, "00_ProjectWide", "Outputs", "Comparisons"), "Numerical")
    save_db(field_db, os.path.join(root_folder, "00_ProjectWide"))
    delete_old(projectwide_output)

    keep_fields = ["FID", "Shape", "POINT_X", "POINT_Y", "SnapDist", "FldRchLen"]

    to_merge = []

    # Check to see if the user is using the field CSV input, set the field lists to the values from that file
    if is_csv(input_field_csv):
        pnet_fields, field_db_fields, new_fields_initial = read_field_csv(input_field_csv)

    for watershed in watershed_folders:

        old_pnet_fields = pnet_fields
        old_field_db_fields = field_db_fields
        old_new_fields_initial = new_fields_initial

        arcpy.AddMessage("Working on {}...".format(watershed))

        # Setup watershed data
        watershed_output = make_folder(os.path.join(watershed, "Outputs", "Comparisons"), "Numerical")
        delete_old(watershed_output)

        # Get the CSV with extracted PNET data
        watershed_pnet = os.path.join(watershed, "Outputs", "Extracted_Data", "All_Data.csv")

        # Get data from the PNET output
        pnet_data_list = csv_to_list(watershed_pnet)

        # Find certain PNET indexes in the PNET output
        id_pnet = pnet_data_list[0].index("""RchID""")
        pnet_indexes = []
        missing_field_indexes = []
        for pnet_field in old_pnet_fields:
            if pnet_field in pnet_data_list[0]:
                pnet_indexes.append(pnet_data_list[0].index(pnet_field))
            else:
                missing_field_indexes.append(old_pnet_fields.index(pnet_field))

        # remove headers
        pnet_data_list.pop(0)

        # Create a list with only necessary data
        pnet_compare_list = []
        for row in pnet_data_list:
            to_add = []
            # Add id column
            to_add.append(row[id_pnet])
            # Add any other columns
            for index in pnet_indexes:
                to_add.append(row[index])
            pnet_compare_list.append(to_add)

        # Get the CSV with Field data
        watershed_db = save_db(field_db, watershed)

        # Get data from the field database
        field_data_list = csv_to_list(watershed_db)

        # Find certain field indexes in the field database
        id_field_db = field_data_list[0].index("""RchID""")
        field_indexes_db = []
        for field_db_field in old_field_db_fields:
            if old_field_db_fields.index(field_db_field) not in missing_field_indexes:
                field_indexes_db.append(field_data_list[0].index(field_db_field))

        # remove headers
        field_data_list.pop(0)

        # Create a list with only necessary data
        field_compare_list = []
        for row in field_data_list:
            to_add = []
            # Add id column
            to_add.append(row[id_field_db])
            # Add any other columns
            for index in field_indexes_db:
                to_add.append(row[index])
            field_compare_list.append(to_add)

        # Make list of new fields
        new_fields = ["""RchID"""]
        for new_field in old_new_fields_initial:
            if old_new_fields_initial.index(new_field) not in missing_field_indexes:
                # make sure the field can fit into an arcmap field
                # This is where PNET data will go
                new_fields.append("pnet_" + new_field[:5])
                # This is where field database data will go
                new_fields.append("fld_" + new_field[:5])
                # This is where actual difference data will go
                new_fields.append("dif_" + new_field[:5])
                # This is where percent difference data will go
                new_fields.append("pdif_" + new_field[:5])
                # This is where ratio data will go
                new_fields.append("rtio_" + new_field[:5])


        # Perform data comparisons

        both_compare_list = [new_fields]

        for pnet_row in pnet_compare_list:
            new_row = []
            # Get the ID of the current row
            current_site = pnet_row[0]
            # Find the corresponding row in the field data list
            for db_row_num, db_row in enumerate(field_compare_list):
                # If the two site are the same
                if db_row[0] == current_site:
                    field_row = db_row
                    break

            # Add the reach ID to our new row
            new_row.append(pnet_row[0])

            # Prepare to iterate through each column of data, skipping rchID
            pnet_iter = iter(pnet_row)
            field_iter = iter(field_row)
            next(pnet_iter)
            next(field_iter)

            for pnet_data, field_data, in zip(pnet_iter, field_iter):

                # Make sure that the data is not missing
                if pnet_data != "" and field_data != "" and pnet_data != '0' and field_data != '0':

                    # Add data into the new row
                    pnet_num = float(pnet_data)
                    field_num = float(field_data)
                    new_row.append(pnet_num)
                    new_row.append(field_num)

                    # Add actual difference field
                    new_row.append(pnet_num-field_num)

                    # Add percent difference field
                    if field_num > 0 or field_num < 0:
                        if pnet_num > field_num:
                            new_row.append((pnet_num-field_num)/pnet_num)
                        else:
                            new_row.append((field_num-pnet_num)/field_num)

                        # Add ratio field
                        new_row.append(float(pnet_num/field_num))
                    else:
                        new_row.append(0.0)
                        new_row.append(0.0)
                        new_row.append(0.0)


                else:
                    new_row += [0, 0, 0, 0, 0]

            both_compare_list.append(new_row)

        # Add in data for each of the other PNET fields
        pnet_data_list = csv_to_list(watershed_pnet)
        for row_num, row in enumerate(both_compare_list):
            # Add data from each PNET field
            data_to_add = []
            for add_field in keep_fields:
                if add_field in pnet_data_list[0]:
                    this_index = pnet_data_list[0].index(add_field)
                    data_to_add.append(pnet_data_list[row_num][this_index])
            both_compare_list[row_num] = data_to_add + row


        # Create a new shapefile to hold data
        template = os.path.join(watershed, "Outputs", "Extracted_Data", "Extraction_Merge_Points.shp")
        comparison_points = arcpy.CreateFeatureclass_management(watershed_output, "Numerical_Comparison_Points.shp",
                                                                "POINT", spatial_reference=template)

        # Add in new fields to the shapefile
        for field, example in zip(both_compare_list[0], both_compare_list[1]):
            # Make sure we are not adding in any already existing default fields
            shapefile_fields = get_fields(comparison_points)
            if field not in shapefile_fields:
                # Decide to add a text or float field
                if isinstance(example, str):
                    arcpy.AddField_management(comparison_points, field, "TEXT")
                else:
                    arcpy.AddField_management(comparison_points, field, "FLOAT")

        # Skip headers
        iter_list = iter(both_compare_list)
        next(iter_list)

        # remove useless field
        arcpy.DeleteField_management(comparison_points, "Id")

        # Add in data to the shapefile
        with arcpy.da.InsertCursor(comparison_points, '*') as inserter:
            with arcpy.da.SearchCursor(template, '*') as searcher:
                for row, search_row in zip(iter_list, searcher):
                    row[1] = search_row[1]
                    inserter.insertRow(row)

        to_merge.append(comparison_points)

        # Save as CSV
        create_csv(os.path.join(watershed_output, "Numerical_Comparison_Data.csv"), comparison_points)

        # Make plots from points
        plot_list = get_fields(comparison_points)
        field_plot_list = []
        pnet_plot_list = []
        for field in plot_list:
            if field.startswith('pnet_'):
                pnet_plot_list.append(field)
            elif field.startswith('fld_'):
                field_plot_list.append(field)

        create_plots(comparison_points, pnet_plot_list, field_plot_list, old_new_fields_initial, watershed_output)


    arcpy.AddMessage('Saving ProjectWide...')
    merged = arcpy.Merge_management(to_merge, os.path.join(projectwide_output, "Numerical_Comparison_Points.shp"))
    create_csv(os.path.join(projectwide_output, "Numerical_Comparison_Data.csv"), merged)

    # Make plots from points
    plot_list = get_fields(merged)
    field_plot_list = []
    pnet_plot_list = []
    for field in plot_list:
        if field.startswith('pnet_'):
            pnet_plot_list.append(field)
        elif field.startswith('fld_'):
            field_plot_list.append(field)

    create_plots(merged, pnet_plot_list, field_plot_list, new_fields_initial, projectwide_output)


def save_db(database, main_folder):
    save_loc = os.path.join(main_folder, "Inputs", "Database", "Field_Database.csv")
    shutil.copyfile(database, save_loc)
    return save_loc


def create_plots(comparison_points, pnet_plot_fields, field_plot_fields, field_names, out_folder):

    for pnet_field, field_field, field_name in zip(pnet_plot_fields, field_plot_fields, field_names):
        x, y = clean_values(comparison_points, pnet_field, field_field)
        if len(x) > 1 and len(y) > 1:
            # set up plot
            fig = plt.figure()
            fig.add_axes()
            ax = fig.add_subplot(111)

            # set axis range

            new_min = min([min(x), min(y)])
            new_max = max([max(x), max(y)])
            range = new_max-new_min
            buffer = range/30
            ax.set_xlim(new_min-buffer, max(x)+buffer, 1)
            ax.set_ylim(new_min-buffer, max(y)+buffer, 1)
            ax.set_aspect(aspect='equal')
            plt.setp(ax.get_xticklabels(), rotation=90, horizontalalignment='right')
            a = math.floor((math.log10(range / 10))*-1)
            increment = round(range, int(a)) / 10
            plt.xticks(np.arange(0, max(x) + buffer, step=increment))
            plt.yticks(np.arange(0, max(y) + buffer, step=increment))

            # plot data points, regression line, 1:1 reference

            plot_points(x, y, ax)
            if len(x) > 1:
                r2_value, slope, intercept = plot_regression(x, y, ax, new_max)
                ax.plot([0, new_max], [0, new_max], color='blue', linewidth=1.5, linestyle=":", label='Line of Perfect Agreement')

                ax.set(title='PNET {0} vs. Field Measured {0} (R2 = {1})'.format(field_name, round(r2_value, 2)),
                       xlabel='PNET\n Regression = {}x + {}\n n = {}'.format(round(slope,2), round(intercept,2), len(x)),
                       ylabel='Field Measured')

                # save plot
                plot_name = os.path.join(out_folder, "{}_Plot.png".format(field_name))
                plt.savefig(plot_name, bbox_inches='tight')
                plt.close()


def clean_values(output_points, pnet_field, field_db_field):

    # Pull comparison values from the comparison points shapefile
    x = arcpy.da.FeatureClassToNumPyArray(output_points, [pnet_field]).astype(np.float)
    y = arcpy.da.FeatureClassToNumPyArray(output_points, [field_db_field]).astype(np.float)

    # Remove negatives and zeros
    keep_x = np.where(x > 0.0)
    x = x[keep_x]
    y = y[keep_x]

    keep_y = np.where(y > 0.0)
    x = x[keep_y]
    y = y[keep_y]

    return x, y


def plot_points(x, y, axis):

    axis.scatter(x, y, color="darkred", label="Field Sites", alpha=.4)


def plot_regression(x, y, axis, new_max):

    # calculate regression
    regression = stat.linregress(x, y)
    model_x = np.arange(0.0, new_max, new_max/10000)
    model_y = regression.slope * model_x + regression.intercept
    # plot regression line
    axis.plot(model_x, model_y,  color='black', linewidth=2.0, linestyle='-', label='Regression line')
    # calculate prediction intervals and plot as shaded areas
    n = len(x)

    return regression.rvalue**2, regression.slope, regression.intercept


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
