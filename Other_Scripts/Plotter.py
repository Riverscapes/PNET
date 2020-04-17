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

# The folder where you want outputs stored
out_folder = r''
# The csv containing all field data
field_csv = r''
# The csv containing all pnet data
pnet_csv = r''
# CSV to set field data from instead (optional, expects headers)
input_field_csv = r''


def main():

    # Initialize variables and file locations
    arcpy.env.overwriteOutput = True
    pnet_fields, field_db_fields, new_fields_initial = read_field_csv(input_field_csv)

    # Plot Data
    create_plots(pnet_fields, field_db_fields, new_fields_initial, out_folder)


def create_plots(pnet_plot_fields, field_plot_fields, field_names, out_folder):

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

            if field_name != 'Sinuosity':
                plt.xticks(np.arange(0, max(x) + buffer, step=increment))
                plt.yticks(np.arange(0, max(y) + buffer, step=increment))
            else:
                plt.xticks(np.arange(1, max(x) + buffer, step=increment))
                plt.yticks(np.arange(1, max(y) + buffer, step=increment))

            # plot data points, regression line, 1:1 reference

            plot_points(x, y, ax)
            if len(x) > 1:
                r2_value, slope, intercept = plot_regression(x, y, ax, new_max)
                ax.plot([0, new_max], [0, new_max], color='blue', linewidth=1.5, linestyle=":", label='Line of Perfect Agreement')
                comment = 'PNET Field: {}\n PIBO Field: {}'.format(pnet_field, field_field)
                ax.set(title='PNET {0} vs. PIBO {0} (R2 = {1}\n{2})'.format(field_name, round(r2_value, 2), comment),
                       xlabel='PNET\n Regression = {}x + {}\n n = {}'.format(round(slope,2), round(intercept,2), len(x)),
                       ylabel='Field Measured')

                plot_name = os.path.join(out_folder, "{}_Plot.png".format(field_name))
                plt.savefig(plot_name, bbox_inches='tight')
                plt.close()


def clean_values(pnet_field, field_db_field):

    # Pull comparison values from the comparison points shapefile
    x = arcpy.da.TableToNumPyArray(pnet_csv, [pnet_field]).astype(np.float)
    y = arcpy.da.TableToNumPyArray(field_csv, [field_db_field]).astype(np.float)

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

    list_a, list_b, list_c = [], [], []

    for unique_field in input_field_list:
        list_a.append(unique_field[0])
        list_b.append(unique_field[1])
        list_c.append(unique_field[2])

    return list_a, list_b, list_c


if __name__ == "__main__":
    main()
