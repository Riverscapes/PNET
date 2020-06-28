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
# Name:        Plotter
# Purpose:     Graphs Comparison Data (THis is a script version of part of step 9)
# Author:      Tyler Hatch
#
# Created:     3/1/2020
# Latest Update: 3/1/2020
# -------------------------------------------------------------------------------

# The folder containing all watershed folders
root_folder = arcpy.GetParameterAsText(0)
# The folder containing all watershed folders
input_field_csv = arcpy.GetParameterAsText(1)


def main():

    # Initialize variables and file locations
    arcpy.env.overwriteOutput = True
    watershed_folders = get_watershed_folders(root_folder)
    watershed_folders.insert(0, os.path.join(root_folder, "00_Projectwide"))

    for watershed in watershed_folders:

        arcpy.AddMessage("Working on {}...".format(watershed))
        in_folder = os.path.join(watershed, "Outputs", "Comparisons", "Numerical")
        out_folder = make_folder(os.path.join(watershed, "Outputs", "Comparisons", "Numerical"), "Plots")
        delete_old(in_folder, '.png')
        delete_old(out_folder, '.png')
        data_csv = os.path.join(in_folder, "Numerical_Comparison_Data.csv")

        outliers_csv = os.path.join(root_folder, "00_Projectwide", "Outputs", "Comparisons", "Numerical", "Outliers.csv")
        outlier_fields, outlier_reaches_list = read_outliers_csv(outliers_csv)

        pnet_names, pnet_fields, field_names, field_db_fields, new_fields_initial, pnet_valid, field_valid = read_field_csv(input_field_csv)

        # Plot Data
        create_plots(pnet_names, pnet_fields, field_names, field_db_fields, new_fields_initial, out_folder, data_csv, pnet_valid, field_valid, outlier_fields, outlier_reaches_list)


def create_plots(pnet_names, pnet_plot_fields, field_names, field_plot_fields, new_names, out_folder, data_csv, pnet_valid_list, field_valid_list, outlier_fields, outlier_reaches_list):

    field_list = get_fields(data_csv)
    plots_length = len(pnet_names)
    for count, (pnet_name, pnet_field, field_name, field_field,
                new_name, is_pnet_valid, is_field_valid, outlier_field, outlier_reaches) in \
            enumerate(zip(pnet_names, pnet_plot_fields, field_names, field_plot_fields,
                          new_names, pnet_valid_list, field_valid_list, outlier_fields, outlier_reaches_list)):

        x, y = clean_values(pnet_field, field_field, data_csv, is_pnet_valid, is_field_valid,
                            field_list, outlier_field, outlier_reaches)

        if len(x) > 1 and len(y) > 1:
            arcpy.AddMessage("\tPlotting {} ({}/{})...".format(new_name, count+1, plots_length))
            # set up plot
            fig = plt.figure()
            fig.add_axes()
            ax = fig.add_subplot(111)

            # set axis range
            x_range = max(x) - min(x)
            y_range = max(y) - min(y)

            x_buffer = x_range/30
            y_buffer = y_range/30

            ax.set_xlim(min(x) - x_buffer, max(x) + x_buffer, 1)
            ax.set_ylim(min(y) - y_buffer, max(y) + y_buffer, 1)

            #ax.set_aspect(aspect='equal')

            if pnet_name == "Sinuosity":
                x_origin = 1
            else:
                x_origin = 0
            if field_name == "Sin":
                y_origin = 1
            else:
                y_origin = 0

            plt.setp(ax.get_xticklabels(), rotation=90, horizontalalignment='right')

            if (x_range < .000001):
                arcpy.AddMessage("\t\tCould not plot {}, X value range is too low.".format(new_name))
            else:

                tick_x = float(x_range)/10.0
                a = math.floor((math.log10(tick_x))*-1)
                increment = round(x_range, int(a)) / 10.0
                plt.xticks(np.arange(x_origin, max(x) + x_buffer, step=increment))

                tick_y = float(y_range) / 10.0
                a = math.floor((math.log10(tick_y)) * -1)
                increment = round(y_range, int(a)) / 10.0
                plt.yticks(np.arange(y_origin, max(y) + y_buffer, step=increment))

                # plot data points, regression line, 1:1 reference

                plot_points(x, y, ax)
                if len(x) > 1:

                    r2_value, slope, intercept = plot_regression(x, y, ax, max(x))
                    new_max = max(max(x), max(y))
                    if needs_percent_conversion(x_range, y_range):
                        conversion_factor = 100
                    else:
                        conversion_factor = 1
                    ax.plot([0, new_max*conversion_factor], [0, new_max], color='blue', linewidth=1.5, linestyle=":", label='Line of Perfect Agreement')
                    comment = 'PNET Field: {}\n PIBO Field: {}'.format(pnet_name, field_name)
                    ax.set(title='Comparison Name: {0} \n(R2 = {1}\n{2})'.format(new_name, round(r2_value, 3), comment),
                           xlabel='PNET Value\n\n Regression = {}x + {}\n n = {}'.format(round(slope,2), round(intercept,2), len(x)),
                           ylabel='PIBO value')

                    plot_name = os.path.join(out_folder, "{}_VS_{}.png".format(field_name, pnet_name))
                    plt.savefig(plot_name, bbox_inches='tight')
                    plt.close()
        else:
            arcpy.AddMessage("\tCould not plot, no valid data {}...".format(new_name))


def needs_percent_conversion(r_x,r_y):
    # Returns true if the line of best fit must be converted from decimals to percents
    return(r_x <= 1 and r_y > 15)


def clean_values(pnet_field, field_db_field, data_csv, x_valid, y_valid, field_list, outlier_field, outlier_reaches):

    if pnet_field in field_list and field_db_field in field_list:
        # Pull comparison values from the comparison points shapefile
        x = arcpy.da.TableToNumPyArray(data_csv, [pnet_field]).astype(np.float)
        y = arcpy.da.TableToNumPyArray(data_csv, [field_db_field]).astype(np.float)
        reach_ids = arcpy.da.TableToNumPyArray(data_csv, ["RchID"]).astype(str)


        # Remove outliers in a really inefficient way
        for outlier_reach in outlier_reaches:
            new_x = x[np.where(reach_ids != outlier_reach)]
            new_y = y[np.where(reach_ids != outlier_reach)]
            new_reach_ids = reach_ids[np.where(reach_ids != outlier_reach)]
            x = new_x
            y = new_y
            reach_ids = new_reach_ids


        # Remove negatives and zeros (If zeroes are not valid)
        if x_valid:
            keep_x = np.where(x >= 0.0)
        else:
            keep_x = np.where(x > 0.0)

        x = x[keep_x]
        y = y[keep_x]

        # Remove negatives and zeros (If zeroes are not valid)
        if y_valid:
            keep_y = np.where(y >= 0.0)
        else:
            keep_y = np.where(y > 0.0)

        x = x[keep_y]
        y = y[keep_y]

        return x, y

    return [],[]


def plot_points(x, y, axis):

    axis.scatter(x, y, color="darkred", label="Field Sites", alpha=.4)


def plot_regression(x, y, axis, new_max):

    # Calculate Regression
    regression = stat.linregress(x, y)
    model_x = np.arange(0.0, new_max, new_max/10000)
    model_y = regression.slope * model_x + regression.intercept
    # plot regression line
    axis.plot(model_x, model_y,  color='black', linewidth=2.0, linestyle='-', label='Regression line')
    # calculate prediction intervals and plot as shaded areas
    n = len(x)
    return regression.rvalue**2, regression.slope, regression.intercept


def read_field_csv(file):

    input_field_list = csv_to_list(file)

    # remove headers
    input_field_list.pop(0)

    list_a, list_b, list_c, list_d, list_e, list_f, list_g = [], [], [], [], [], [], []

    for unique_field in input_field_list:
        list_a.append(unique_field[0])
        list_b.append("pn_" + unique_field[2][:7])
        list_c.append(unique_field[1])
        list_d.append("fd_" + unique_field[2][:7])
        list_e.append(unique_field[2])
        list_f.append(parse_valid_text(unique_field[3]))
        list_g.append(parse_valid_text(unique_field[4]))

    return list_a, list_b, list_c, list_d, list_e, list_f, list_g


def parse_valid_text(valid_text):
    return valid_text in ["Y", 'y', "yes", "Yes", "True", "true"]


def read_outliers_csv(to_read):

    to_read_list = csv_to_list(to_read)
    fields = []
    outliers = []
    curr_outliers = []

    for row in to_read_list:

        # This represents a new field
        if len(row) < 2:
            fields.append(row[0])
            outliers.append(curr_outliers)
            curr_outliers = []

        # We are reading in outliers
        else:
            # Use row[1] to skip over id field
            curr_outliers.append(row[1])

    # Remove blank first entry
    outliers.pop(0)

    # Add in final outliers
    outliers.append(curr_outliers)

    return fields, outliers


if __name__ == "__main__":
    main()
