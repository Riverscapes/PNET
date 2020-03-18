import arcpy
import os
from PNET_Functions import get_watershed_folders, delete_old, finish, \
    delete_temps, write_fields_to_text
# -------------------------------------------------------------------------------
# Name:        PNET Step 5
# Purpose:     Cleans up data, adds length field
#
# Author:      Tyler Hatch
#
# Created:     2/15/2020
# Latest Update: 1/22/2020
# -------------------------------------------------------------------------------


# A list of file locations pointing to each watershed's All_points folder
root_folder = arcpy.GetParameterAsText(0)


def main():

    # Initialize variables and file locations
    arcpy.env.overwriteOutput = True

    watershed_folders = get_watershed_folders(root_folder)
    projectwide_output = os.path.join(root_folder, "00_ProjectWide", "Intermediates", "Extraction", "Inputs")
    temps_to_delete = []
    keep_fields = ["Shape", "FID", "SiteID", "RchID", "POINT_X", "POINT_Y", "SnapDist"]
    to_merge_reaches = []
    to_merge_points = []
    delete_old(os.path.join(root_folder, "00_ProjectWide", "Inputs", "Parameters"))


    delete_old(projectwide_output)

    for watershed in watershed_folders:
        arcpy.AddMessage("Starting {}...".format(watershed))

        # Get necessary files
        output_folder = os.path.join(watershed, "Intermediates", "Extraction", "Inputs")
        in_reaches = os.path.join(watershed, "Intermediates", "Reach_Editing", "Outputs", "Field_Reaches.shp")
        in_points = os.path.join(watershed, "Intermediates", "Reach_Editing", "Outputs", "Field_Points.shp")
        points_temp = os.path.join(output_folder, "p_temp.shp")
        reaches_temp = os.path.join(output_folder, "r_temp.shp")
        reaches_joined = os.path.join(output_folder, "r_join.shp")
        points_joined = os.path.join(output_folder, "p_join.shp")
        temps_to_delete.extend([points_temp, reaches_temp, reaches_joined, points_joined])
        points_final = os.path.join(output_folder, "Field_Points_Clean.shp")
        reaches_final = os.path.join(output_folder, "Field_Reaches_Clean.shp")

        # Add field for the length of the field reach
        arcpy.Copy_management(in_reaches, reaches_temp)
        field_to_add = "FldRchLen"
        keep_fields.append(field_to_add)
        field_names = [f.name for f in arcpy.ListFields(reaches_temp)]

        if field_to_add not in field_names:
            arcpy.AddField_management(reaches_temp, field_to_add, "DOUBLE")

        arcpy.CalculateField_management(reaches_temp, field_to_add, "!shape.length@meters!", "PYTHON_9.3", "")

        # Reduce points to only BOR points
        points_layer = "Points"
        arcpy.MakeFeatureLayer_management(in_points, points_layer)
        arcpy.SelectLayerByAttribute_management(points_layer, 'NEW_SELECTION', "\"TOR_BOR\" = \'BOR\'")
        arcpy.CopyFeatures_management(points_layer, points_temp)

        # Add all point data to the reaches
        arcpy.SpatialJoin_analysis(reaches_temp, points_temp, reaches_joined, "JOIN_ONE_TO_ONE")

        # Add all reach data to the points
        arcpy.SpatialJoin_analysis(points_temp, reaches_temp, points_joined, "JOIN_ONE_TO_ONE")

        # Only keep fields we need
        shapes = [points_joined, reaches_joined]
        for shape in shapes:

            # Removes all fields from the shapefile that are not in the above list of fields to keep
            field_names = [f.name for f in arcpy.ListFields(shape)]
            delete_fields = []
            for field in field_names:
                if field not in keep_fields:
                    delete_fields.append(field)

            arcpy.DeleteField_management(shape, delete_fields)

        # Save the points and reaches
        to_merge_points.append(arcpy.CopyFeatures_management(points_joined, points_final))
        to_merge_reaches.append(arcpy.CopyFeatures_management(reaches_joined, reaches_final))

    arcpy.AddMessage("Saving Projectwide...")
    arcpy.Merge_management(to_merge_points, os.path.join(projectwide_output, "Field_Points_Clean"))
    arcpy.Merge_management(to_merge_reaches, os.path.join(projectwide_output, "Field_Reaches_Clean"))

    delete_temps(temps_to_delete)
    finish()


if __name__ == "__main__":
    main()
