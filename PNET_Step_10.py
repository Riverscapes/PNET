import arcpy
import os
import shutil
from PNET_Functions import get_watershed_folders, delete_old, create_csv, \
    get_fields, csv_to_list, parse_multistring, make_folder
import scipy.stats as stat
import numpy as np
import matplotlib.pyplot as plt
import math

# -------------------------------------------------------------------------------
# Name:        PNET Step 10
# Purpose:     Creates Comparison Graphs for categorical data
#
# Author:      Tyler Hatch
#
# Created:     3/1/2020
# Latest Update: 3/1/2020
# -------------------------------------------------------------------------------

# The folder containing all watershed folders
root_folder = arcpy.GetParameterAsText(0)
# CSV to set field data from instead (expects headers)
input_field_csv = arcpy.GetParameterAsText(1)


def main():
    # Initialize variables and file locations
    arcpy.env.overwriteOutput = True
    watershed_folders = get_watershed_folders(root_folder)

    # Setup projectwide data
    projectwide_output = make_folder(os.path.join(root_folder, "00_ProjectWide", "Outputs", "Comparisons"), "Categorical")
    projectwide_database = os.path.join(root_folder, "00_ProjectWide", "Inputs", "Database", "Field_Database.csv")
    delete_old(projectwide_output)

    keep_fields = ["FID", "Shape", "POINT_X", "POINT_Y", "SnapDist", "FldRchLen","EcoRgn_L4" ,"EcoRgn_L3" ,"HUC8" ,"NAME" ,"StreamName"]

    to_merge = []

    #  set the field lists to the values from the file
    # meta_group_field, meta_group_field_name, group_field, group_field_name, field_db_fields = read_field_csv(input_field_csv)

    graphs = read_field_csv_new(input_field_csv)

    for graph in graphs:

        meta_group_field = graph[0]
        meta_group_field_name = graph[1]
        group_field = graph[2]
        group_field_name = graph[3]
        field_db_fields = graph[4]

        for watershed in watershed_folders:

            arcpy.AddMessage("Working on {}...".format(watershed))

            # Setup watershed data
            watershed_output = make_folder(os.path.join(watershed, "Outputs", "Comparisons"), "Categorical")
            delete_old(watershed_output)

            # Get the CSV with Field data
            watershed_db = projectwide_database

            # Get data from the field database
            field_data_list = csv_to_list(watershed_db)

            # Find certain field indexes in the field database

            id_field_db = field_data_list[0].index("""RchID""")
            field_indexes_db = []
            for field_db_field in field_db_fields:
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

            # Get the CSV with extracted PNET data
            watershed_pnet = os.path.join(watershed, "Outputs", "Extracted_Data", "All_Data.csv")

            # Get data from the PNET output
            pnet_data_list = csv_to_list(watershed_pnet)

            # Find certain PNET indexes in the PNET output
            id_pnet = pnet_data_list[0].index("""RchID""")
            if group_field not in pnet_data_list[0] or meta_group_field not in pnet_data_list[0]:
                arcpy.AddMessage("Could not complete plots for {}, could not find {} field or {} field".format(watershed, group_field, meta_group_field))
            else:
                group_pnet = pnet_data_list[0].index(group_field)
                meta_group_pnet = pnet_data_list[0].index(meta_group_field)

                # remove headers
                pnet_data_list.pop(0)

                # Create a list with only necessary data
                pnet_compare_list = []
                for row in pnet_data_list:
                    to_add = []
                    # Add id column
                    to_add.append(row[id_pnet])
                    # Add grouping columns
                    to_add.append(row[group_pnet])
                    to_add.append(row[meta_group_pnet])
                    # Add this row to the overall list
                    pnet_compare_list.append(to_add)

                # Make list of new fields
                new_fields = ["""RchID""", meta_group_field_name, group_field_name]
                for new_field in field_db_fields:
                    # This is where field data will go
                    new_fields.append("Y_" + new_field[:7])

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
                    # Add the metagroup to our new row
                    new_row.append(pnet_row[1])
                    # Add the group to our new row
                    new_row.append(pnet_row[2])

                    # Prepare to iterate through each column of data, skipping rchID
                    field_iter = iter(field_row)
                    next(field_iter)

                    for field_data in field_iter:

                        # Make sure that the data is not missing
                        if field_data != "":

                            # Add data into the new row
                            field_num = float(field_data)
                            new_row.append(field_num)

                        else:
                            new_row += 0

                    both_compare_list.append(new_row)

                # Add in data for each of the other PNET fields (That were created in previous steps)
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
                comparison_points = arcpy.CreateFeatureclass_management(watershed_output, "Categorical_Comparison_Points.shp",
                                                                        "POINT", spatial_reference=template)
                to_merge.append(comparison_points)

                # Add in new fields to the shapefile
                for field, example in zip(both_compare_list[0], both_compare_list[1]):
                    # Make sure we are not adding in any already existing default fields
                    shapefile_fields = get_fields(comparison_points)
                    if field not in shapefile_fields:
                        # Decide to add a text or float field
                        if isinstance(example, str):
                            arcpy.AddField_management(comparison_points, field[:10], "TEXT")
                        else:
                            arcpy.AddField_management(comparison_points, field[:10], "FLOAT")

                # Skip headers
                iter_list = iter(both_compare_list)
                next(iter_list)


                # remove useless field
                arcpy.DeleteField_management(comparison_points, "Id")

                # Add in data to the shapefile
                with arcpy.da.InsertCursor(comparison_points, '*') as inserter:
                    with arcpy.da.SearchCursor(template, '*') as searcher:
                        for row, search_row in zip(iter_list, searcher):
                            # Steal Shape and FID data from template
                            row.insert(0, search_row[1])
                            row.insert(0, search_row[0])
                            # Add in row
                            inserter.insertRow(row)

                # Save as CSV
                create_csv(os.path.join(watershed_output, "Categorical_Comparison_Data.csv"), comparison_points)

                # Get a list of all the different metagroup types
                metagroup_types = unique_values(comparison_points, meta_group_field_name[:10])

                # Make a folder, shapefile, and plots for every metagroup
                if " " in metagroup_types:
                    metagroup_types.remove(" ")

                for metagroup in metagroup_types:

                    # Create a new folder for only data in this meta group
                    plot_folder = make_folder(watershed_output, "{}_{}".format(meta_group_field_name.title(), metagroup.title()))

                    # Create a shapefile with only data we want to look at
                    layer_name = 'temp'
                    new_shapefile = os.path.join(plot_folder, '{}_{}_Comparison.shp'.format(meta_group_field_name.title(), metagroup.title()))
                    arcpy.MakeFeatureLayer_management(comparison_points, layer_name)
                    query = '{} = \'{}\''.format(meta_group_field_name[:10], metagroup)
                    arcpy.SelectLayerByAttribute_management(layer_name, 'NEW_SELECTION', query)
                    arcpy.CopyFeatures_management(layer_name, new_shapefile)

                    # Create plots for this data
                    create_plots(new_shapefile, group_field_name, field_db_fields, plot_folder, metagroup, meta_group_field_name)


        # Do projectwide
        arcpy.AddMessage('Saving ProjectWide...')
        merged = arcpy.Merge_management(to_merge, os.path.join(projectwide_output, "Categorical_Comparison_Points.shp"))
        create_csv(os.path.join(projectwide_output, "Categorical_Comparison_Data.csv"), merged)

        # Get a list of all the different metagroup types
        metagroup_types = unique_values(merged, meta_group_field_name[:10])

        # Make a folder, shapefile, and plots for every metagroup
        if " " in metagroup_types:
            metagroup_types.remove(" ")

        for metagroup in metagroup_types:
            # Create a new folder for only data in this meta group
            plot_folder = make_folder(projectwide_output, "{}_{}".format(meta_group_field_name.title(), metagroup.title()))

            # Create a shapefile with only data we want to look at
            layer_name = 'temp'
            new_shapefile = os.path.join(plot_folder,
                                         '{}_{}_Comparison.shp'.format(meta_group_field_name.title(), metagroup.title()))
            arcpy.MakeFeatureLayer_management(merged, layer_name)
            query = '{} = \'{}\''.format(meta_group_field_name[:10], metagroup)
            arcpy.SelectLayerByAttribute_management(layer_name, 'NEW_SELECTION', query)
            arcpy.CopyFeatures_management(layer_name, new_shapefile)

            # Create plots for this data
            create_plots(new_shapefile, group_field_name, field_db_fields, plot_folder, metagroup, meta_group_field_name)


def create_plots(data_shapefile, group_field, y_axis_fields, out_folder, metagroup, metagroup_name):

    for y_axis_field in y_axis_fields:
        labels, all_data = get_data(data_shapefile, group_field, y_axis_field)
        new_labels = []
        for entry, label in zip(all_data, labels):
            n = len(entry)
            new_label = "[{}] ".format(n) + label
            new_labels.append(new_label)

        # set up plot
        fig, ax = plt.subplots(nrows=1, ncols=1, figsize=(9, 9))

        bplot = ax.boxplot(all_data,
                           vert=True,  # vertical box alignment
                           labels=new_labels)  # will be used to label x-ticks

        ax.set_title('{} field values for all {} groups\n [When {} = {}]'
                      .format(y_axis_field.title(), group_field.title(), metagroup_name.title(), metagroup.title()))

        ax.yaxis.grid(True)
        ax.set_xlabel('{} Category'.format(group_field.title()))
        ax.set_ylabel('{} Value'.format(y_axis_field.title()))
        plt.xticks(rotation=90)

        # save plot
        plot_name = os.path.join(out_folder, "{}_Plot.png".format(y_axis_field.title()))
        plt.savefig(plot_name, bbox_inches='tight')
        plt.close()


def get_data(data_shapefile, group_field, y_axis_field):

    # Pull comparison values from the comparison points shapefile
    actual_group_field = group_field[:10]
    actual_y_axis_field = "Y_" + y_axis_field[:7]

    groups_list = unique_values(data_shapefile, actual_group_field)
    data = []

    for group in groups_list:

        query = '{} = \'{}\''.format(actual_group_field, group)
        group_data = arcpy.da.FeatureClassToNumPyArray(data_shapefile, actual_y_axis_field, query).astype(np.float)

        # Remove negatives and zeros
        group_data = group_data[np.where(group_data > 0.0)]

        data.append(group_data)

    return groups_list, data


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


def save_db(database, main_folder):
    save_loc = os.path.join(main_folder, "Inputs", "Database", "Field_Database.csv")
    shutil.copyfile(database, save_loc)
    return save_loc


def read_field_csv(file):

    input_field_list = csv_to_list(file)

    # remove headers
    input_field_list.pop(0)

    meta = input_field_list[0][0]
    meta_name = input_field_list[0][1]
    group = input_field_list[0][2]
    group_name = input_field_list[0][3]
    fields = [input_field_list[0][4]]

    # remove top row
    input_field_list.pop(0)

    for y_axis_field in input_field_list:
        fields.append(y_axis_field[4])

    return meta, meta_name, group, group_name, fields



def read_field_csv_new(file):
    input_field_list = csv_to_list(file)

    # remove headers
    input_field_list.pop(0)

    end_graph = False
    fields = []
    graphs = []

    for row in input_field_list:

        if len(row[2]) > 1:
            if end_graph:
                graphs.append(meta, meta_name, group, group_name, fields)

            # Start a new graph
            meta = row[0]
            meta_name = row[1]
            group = row[2]
            group_name = row[3]
            fields = [row[4]]
            end_graph = True

        else:
            fields.append(row[4])

    # Add final row
    graphs.append(meta, meta_name, group, group_name, fields)

    return graphs


def is_csv(file):
    return file.endswith('.csv')


def unique_values(table, field):

    # Adapted from https://gis.stackexchange.com/questions/208430/trying-to-extract-a-list-of-unique-values-from-a-field-using-python
    with arcpy.da.SearchCursor(table, [field]) as cursor:
        return sorted({row[0] for row in cursor})


if __name__ == "__main__":
    main()
