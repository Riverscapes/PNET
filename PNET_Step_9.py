import arcpy
import os
import shutil
from PNET_Functions import get_watershed_folders, delete_old, create_csv, get_fields, csv_to_list, parse_multistring
import scipy.stats as stat
import numpy as np
import matplotlib.pyplot as plt

# -------------------------------------------------------------------------------
# Name:        PNET Step 9
# Purpose:     Creates Comparison Fields
#
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


def main():
    # Initialize variables and file locations
    arcpy.env.overwriteOutput = True
    watershed_folders = get_watershed_folders(root_folder)

    # Setup projectwide data
    projectwide_output = os.path.join(root_folder, "00_ProjectWide", "Outputs", "Comparisons")
    save_db(field_db, os.path.join(root_folder, "00_ProjectWide"))
    delete_old(projectwide_output)

    keep_fields = ["FID", "Shape", "POINT_X", "POINT_Y", "SnapDist"]

    to_merge = []

    for watershed in watershed_folders:

        arcpy.AddMessage("Working on {}...".format(watershed))

        # Setup watershed data
        watershed_output = os.path.join(watershed, "Outputs", "Comparisons")
        delete_old(watershed_output)

        # Get the CSV with Field data
        watershed_db = save_db(field_db, watershed)

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
        pnet_indexes = []
        for pnet_field in pnet_fields:
            pnet_indexes.append(pnet_data_list[0].index(pnet_field))

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

        # Make list of new fields
        new_fields = ["""RchID"""]
        for new_field in new_fields_initial:
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
                if pnet_data != "" and field_data != "":

                    # Add data into the new row
                    pnet_num = float(pnet_data)
                    field_num = float(field_data)
                    new_row.append(pnet_num)
                    new_row.append(field_num)

                    # Add actual difference field
                    new_row.append(pnet_num-field_num)

                    # Add percent difference field
                    if pnet_num > field_num:
                        new_row.append((pnet_num-field_num)/pnet_num)
                    else:
                        new_row.append((field_num-pnet_num)/field_num)

                    # Add ratio field
                    new_row.append(float(pnet_num/field_num))

                else:
                    new_row += [0, 0, 0, 0, 0]

            both_compare_list.append(new_row)

        # Add in data for each of the other PNET fields
        pnet_data_list = csv_to_list(watershed_pnet)
        for row_num, row in enumerate(both_compare_list):
            # Add data from each PNET field
            data_to_add = []
            for add_field in keep_fields:
                this_index = pnet_data_list[0].index(add_field)
                data_to_add.append(pnet_data_list[row_num][this_index])
            both_compare_list[row_num] = data_to_add + row


        # Create a new shapefile to hold data
        template = os.path.join(watershed, "Outputs", "Extracted_Data", "Extraction_Merge_Points.shp")
        comparison_points = arcpy.CreateFeatureclass_management(watershed_output, "Comparison_Points.shp",
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
        create_csv(os.path.join(watershed_output, "Comparison_Data.csv"), comparison_points)

        # Make plots from points
        plot_list = get_fields(comparison_points)
        field_plot_list = []
        pnet_plot_list = []
        for field in plot_list:
            if field.startswith('pnet_'):
                pnet_plot_list.append(field)
            elif field.startswith('fld_'):
                field_plot_list.append(field)

        create_plots(comparison_points, pnet_plot_list, field_plot_list, new_fields_initial, watershed_output)

    arcpy.AddMessage('Saving ProjectWide...')
    merged = arcpy.Merge_management(to_merge, os.path.join(projectwide_output, "Comparison_Points.shp"))
    create_csv(os.path.join(projectwide_output, "Comparison_Data.csv"), merged)

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
        plt.xticks(np.arange(min(x)-buffer, max(x)+buffer, range / 8))
        plt.yticks(np.arange(min(y)-buffer, max(y)+buffer, range / 8))

        # plot data points, regression line, 1:1 reference

        plot_points(x, y, ax)
        if len(x) > 1:
            r2_value = plot_regression(x, y, ax, new_max)
        ax.plot([0, new_max], [0, new_max], color='blue', linewidth=1.5, linestyle=":", label='Line of Perfect Agreement')

        ax.set(title='PNET {0} vs. Field Measured {0} (R2 = {1})'.format(field_name, round(r2_value, 2)),
               xlabel='PNET',
               ylabel='Field Measured')

        # add legend
        legend = plt.legend(loc="upper left", bbox_to_anchor=(1,1))
        # save plot
        plot_name = os.path.join(out_folder, "{}_Plot.png".format(field_name))
        plt.savefig(plot_name, bbox_extra_artists=(legend,), bbox_inches='tight')
        plt.close()


def clean_values(output_points, pnet_field, field_db_field):

    # Pull comparison values from the comparison points shapefile
    x = arcpy.da.FeatureClassToNumPyArray(output_points, [pnet_field]).astype(np.float)
    y = arcpy.da.FeatureClassToNumPyArray(output_points, [field_db_field]).astype(np.float)

    # pull out observed values of zero
    x1 = x[np.nonzero(x)]
    y1 = y[np.nonzero(x)]

    return x1, y1


def plot_points(x, y, axis):

    axis.scatter(x, y, color="darkred", label="Field Sites", alpha=.4)


def plot_regression(x, y, axis, new_max):

    # calculate regression equation of e_DamCt ~ mCC_EX_CT and assign to variable
    regression = stat.linregress(x, y)
    #model_x = np.arange(0.0, round(max(x))+2, 0.1)
    model_x = np.arange(0.0, new_max, new_max/10000)
    model_y = regression.slope * model_x + regression.intercept
    # plot regression line
    axis.plot(model_x, model_y,  color='black', linewidth=2.0, linestyle='-', label='Regression line')
    # calculate prediction intervals and plot as shaded areas
    n = len(x)
    error = stat.t.ppf(1-0.025, n-2) * regression.stderr
    upper_ci = model_y + error
    lower_ci = model_y - error
    #axis.fill_between(model_x, y1=upper_ci, y2=lower_ci, facecolor='red', alpha=0.3, label="95% Confidence Interval")
    # in-plot legend
    axis.legend(loc='best', frameon=False)
    return regression.rvalue**2


if __name__ == "__main__":
    main()
