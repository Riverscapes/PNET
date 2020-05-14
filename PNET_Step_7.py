import arcpy
import os
import re
from PNET_Functions import get_watershed_folders, delete_old, finish, \
    delete_temps, make_folder, create_csv, read_file, keep_fields, get_fields, remove_empty_fields, is_empty

# -------------------------------------------------------------------------------
# Name:        PNET Step 7
# Purpose:     Extracts all Network data to PIBO points and PIBO Reaches
#
# Author:      Tyler Hatch
#
# Created:     10/24/2019
# Latest Update: 1/22/2020
# -------------------------------------------------------------------------------

# The folder containing all watershed folders
root_folder = arcpy.GetParameterAsText(0)
# All segments below this length in meters will not be considered when calculating multi segment reaches.
length_cutoff = int(arcpy.GetParameterAsText(1))


def main():

    # Initialize variables and file locations
    arcpy.env.overwriteOutput = True

    watershed_folders = get_watershed_folders(root_folder)
    projectwide_output = os.path.join(root_folder, "00_ProjectWide", "Intermediates", "Extraction", "Outputs")
    delete_old(projectwide_output)

    to_merge = []
    # Add a bunch of blank lists to the to_merge list, one space for each data network type
    for _ in get_data_networks(watershed_folders[0]):
        to_merge.append([])
    to_delete = []

    # This loops for every watershed
    for watershed_folder in watershed_folders:

        output_folder = os.path.join(watershed_folder, "Intermediates", "Extraction", "Outputs")

        network_list = get_data_networks(watershed_folder)

        arcpy.AddMessage("Starting " + watershed_folder + "...")
        for data_network_count, data_network in enumerate(network_list):
            if not is_empty(data_network):

                old_reaches = os.path.join(watershed_folder, "Intermediates",
                                           "Extraction", "Inputs", "Field_Reaches_Clean.shp")

                # Create a name for this data network so it can have a unique save location
                data_network_name = data_network.replace(os.path.join(watershed_folder, "Inputs", "Data_Networks"), "")
                data_network_name = data_network_name.replace(".shp", "")
                data_network_name = data_network_name.replace("\\", "")

                arcpy.AddMessage("\tStarting {}...".format(data_network_name))

                data_network_folder = make_folder(output_folder, data_network_name)
                delete_old(data_network_folder)

                reaches = os.path.join(data_network_folder, "Reaches_Temp.shp")

                to_delete.append(reaches)

                reaches_save = os.path.join(data_network_folder, data_network_name + "_Points_Extracted.shp")

                arcpy.CopyFeatures_management(old_reaches, reaches)

                # Clip the data network to the Field reaches. This is important for calculating the math later
                clip = os.path.join(data_network_folder, "Clip_Temp.shp")
                to_delete.append(clip)

                arcpy.Clip_analysis(data_network, reaches, clip)
                clipped_data_network = clip

                # Adds field CLIP_LEN, which is the length of the clipped data segment
                arcpy.AddField_management(clipped_data_network, "CLIP_LEN", "DOUBLE")
                arcpy.CalculateField_management(clipped_data_network, "CLIP_LEN", "!shape.length@meters!", "PYTHON_9.3", "")

                # These fields is unnecessary and causes issues with merging, so they are deleted
                field_names = [f.name for f in arcpy.ListFields(clipped_data_network)]
                fields_to_delete = ["Join_Count", "TARGET_FID", "Join_Cou_1"]
                for field in fields_to_delete:
                    if field in field_names:
                        arcpy.DeleteField_management(clipped_data_network, field)

                data_network_fields = get_fields(data_network)
                pnet_fields = get_fields(old_reaches)
                fields_to_keep = pnet_fields + data_network_fields



                # Extracts data from the data network to PIBO reaches using a weighted average system.
                extract_network(reaches, clipped_data_network, reaches_save, data_network_folder, pnet_fields)

                # Remove all unnecessary fields
                keep_fields(reaches_save, fields_to_keep)
                #remove_empty_fields(reaches_save, pnet_fields)

                # Delete any temporary shape files created
                delete_temps(to_delete)



                create_csv(os.path.join(data_network_folder, "{}.csv".format(data_network_name)), reaches_save)
                to_merge[data_network_count].append([reaches_save, data_network_name])

    # Iterate through to_merge, and save a point and network shapefile for each data network

    arcpy.AddMessage("Saving Projectwide...")
    for data_network_type in to_merge:
        to_merge_networks = []
        save_name = data_network_type[0][1]
        save_folder = make_folder(projectwide_output, save_name)
        for watershed in data_network_type:
            to_merge_networks.append(watershed[0])
        csv_save = arcpy.Merge_management(to_merge_networks,
                               os.path.join(save_folder, save_name + "_Points_Extracted.shp"))
        create_csv(os.path.join(save_folder, "{}.csv".format(save_name)), csv_save)

    finish()


def get_data_networks(watershed_folder):

    # Gets a list of all network shapefile locations
    to_return = []
    network_folder = os.path.join(watershed_folder, "Inputs", "Data_Networks")
    for r, d, f in os.walk(network_folder):
        for file in f:
            # This line makes sure it is a shapefile and also ignores the full BRAT network (As we only need perennial)
            if '.shp' in file and '.xml' not in file:
                to_return.append(os.path.join(r, file))

    return to_return


def extract_network(network, data_network, output, data_network_folder, fields_to_keep):

    to_delete = []

    # Create a shapefile to check how many data network segments each field reach overlaps
    spatial_temp = os.path.join(data_network_folder, "spatial_temp.shp")
    to_delete.append(spatial_temp)
    arcpy.SpatialJoin_analysis(network, data_network, spatial_temp, "JOIN_ONE_TO_ONE")
    network = spatial_temp

    # Create a shapefile of Field reaches that only overlap with one data_network segment
    join_one = "JoinOne"
    arcpy.MakeFeatureLayer_management(network, join_one)
    arcpy.SelectLayerByAttribute_management(join_one, 'NEW_SELECTION', 'Join_Count = 1')
    temp = os.path.join(data_network_folder, "JoinOne_Temp.shp")
    to_delete.append(temp)
    arcpy.CopyFeatures_management(join_one, temp)
    join_one = temp

    # Extracts data_network data onto the PIBO reaches with only one data_network segment
    temp2 = os.path.join(data_network_folder, "ExtractedOne_Temp.shp")
    to_delete.append(temp2)
    extracted_one = extract_singles(join_one, data_network, temp2, data_network_folder)
    to_delete.append(extracted_one)

    # Create a shapefile of PIBO reaches that only overlap with multiple data_network segments
    join_mult = "JoinMult"
    arcpy.MakeFeatureLayer_management(network, join_mult)
    arcpy.SelectLayerByAttribute_management(join_mult, 'NEW_SELECTION', 'Join_Count > 1')
    temp3 = os.path.join(data_network_folder, "JoinMult_Temp.shp")
    to_delete.append(temp3)
    arcpy.CopyFeatures_management(join_mult, temp3)
    join_mult = temp3

    # Checks to see how many PIBO reaches overlap multiple data_network segments
    num_rows = arcpy.GetCount_management(join_mult)
    num_rows = int(num_rows[0])

    # This makes sure that we are not trying to extract data onto a file with no reaches
    if num_rows > 0:

        # Extracts data_network data onto the PIBO reaches with only multiple data_network segments
        temp4 = os.path.join(data_network_folder, "ExtractMult_Temp.shp")
        to_delete.append(temp4)
        extracted_mult = extract_multiple(join_mult, data_network, temp4, fields_to_keep, data_network_folder)
        to_delete.append(extracted_mult)
        arcpy.Merge_management([extracted_one, extracted_mult], output)

    else:

        # No merging is necessary, since there were no multiple segment reaches
        arcpy.CopyFeatures_management(extracted_one, output)

    # Delete any temporary shape files created
    delete_temps(to_delete)

    # Return the shapefile with all PIBO reaches, now with data_network data
    return output


def extract_singles(network, data_network, temp, data_network_folder):

    # Performs a spatial join on the single segment PIBO reaches, adding data_network data
    arcpy.SpatialJoin_analysis(network, data_network, temp)
    # Add relevant extraction type fields
    arcpy.AddField_management(temp, "EXT_TYPE", "TEXT")
    arcpy.AddField_management(temp, "EXT_MATH", "TEXT")

    data_points = arcpy.CreateFeatureclass_management(data_network_folder, "Extracted_Points_Single.shp",
                                                      "POINT", temp, spatial_reference=temp)

    with arcpy.da.SearchCursor(temp, '*') as searcher:
        with arcpy.da.InsertCursor(data_points, '*') as inserter:
            for row in searcher:
                inserter.insertRow(row)

    return data_points


def extract_multiple(network, data_network, temp, fields_to_keep, data_network_folder):

    # Clean up the dataset so that we only keep fields we want
    field_names = [f.name for f in arcpy.ListFields(network)]
    fields_to_delete = ["Join_Count", "TARGET_FID", "Join_Cou_1"]
    for field in fields_to_delete:
        if field in field_names:
            arcpy.DeleteField_management(network, field)
    fields_to_keep += fields_to_delete
    keep_fields(network, fields_to_keep)

    # Creates a shapefile with an entry for every data_network segment that overlaps a PIBO reach
    arcpy.SpatialJoin_analysis(network, data_network, temp, "JOIN_ONE_TO_MANY")
    joined = temp
    field_names = [f.name for f in arcpy.ListFields(joined)]
    data_list = []

    # Turns the shapefile from before into a Python list. This is to minimize interaction with cursors.
    with arcpy.da.SearchCursor(joined, '*') as cursor:
        for row in cursor:
            to_add = []
            for count, field in enumerate(field_names):
                to_add.append(row[count])
            data_list.append(to_add)

    # Split the data list by PIBO reach, so that per reach calculations can be done.
    split_list = split_list_by_reach(data_list, field_names)

    # This is where all of the math happens. Each PIBO reach now has the necessary data_network data.
    input_list = combine_segments(split_list, field_names)

    # Add relevant extraction type fields
    arcpy.AddField_management(joined, "EXT_TYPE", "TEXT")
    arcpy.AddField_management(joined, "EXT_MATH", "TEXT")

    # Remove reaches that are repeats from the same join
    field_names = [f.name for f in arcpy.ListFields(joined)]
    if "TARGET_FID" in field_names:
        arcpy.DeleteIdentical_management(joined, "TARGET_FID")

    # Create a new points shapefile to save all of this data
    data_points = arcpy.CreateFeatureclass_management(data_network_folder, "Extracted_Points_Multiple.shp",
                                                      "POINT", joined, spatial_reference=joined)

    # Put extracted data on these points
    with arcpy.da.InsertCursor(data_points, '*') as cursor:
        for input_reach in input_list:
            cursor.insertRow(input_reach)

    return data_points


def split_list_by_reach(segment_list, fields):

    # Initialize Values
    reach = []
    reach_id_index = fields.index("""RchID""")
    return_list = []
    past_reach_id = segment_list[0][reach_id_index]
    need_last = True

    # This loop is to take the list of individual data_network segments, and put them into a new list, grouped by reach
    for seg in segment_list:

        # Adding a segment to the same reach
        if seg[reach_id_index] == past_reach_id:
            reach.append(seg)
            need_last = True

        # Adding a new reach to the return list, then creating a new reach
        else:
            return_list.append(reach)
            reach = [seg]
            past_reach_id = seg[reach_id_index]
            need_last = False

    # This makes sure that the final reach gets added, because it may be missed in the for loop
    if need_last:
        return_list.append(reach)

    # Returns a list of reaches, which each contain a list of segments, which each contain a list of field values
    return return_list


def print_split_list(split_list):
    # This exists only for troubleshooting purposes, prints the reach list in a readable way
    for reach in split_list:
        arcpy.AddMessage("Reach:")
        for segment in reach:
            arcpy.AddMessage("----------",)
            arcpy.AddMessage(segment)


def combine_segments(reach_list, fields):

    # Transpose the reach so that instead of being a list of segments,
    # it is a list of each field and its values within the reach
    for reach in reach_list:
        reach = transpose_reach(reach)

    # Adds and calculate a THRESHOLD field, which informs whether the segment is above or below the length threshold
    fields.append("THRESHOLD")
    reach_list = categorize_short(reach_list, fields)

    # Adds and calculate a TYPE field, which informs the segments relationship to other segments in the reach
    fields.append("TYPE")
    reach_list = categorize_type(reach_list, fields)

    # Adds and calculates the ACTION & MATH field, which informs what needs to be done to the segment for extraction
    fields.append("ACTION")
    fields.append("MATH")
    reach_list = categorize_action(reach_list, fields)

    # Deletes segments whose ACTION was tagged as 'Delete'
    reach_list = delete_unnecessary(reach_list)

    # Does all of the necessary math to calculate data_network values for each reach, based on values and the ACTION field
    reach_list = condense_to_single(reach_list, fields)

    # Removes all added fields (They shouldn't be in the shapefile), and returns the list to the expected format
    reach_list = cleanup(reach_list)

    # Returns a list of every reach, now complete with appropriate data_network data
    return reach_list


def transpose_reach(reach):

    # Flips a reach, so that each field now has its own list of values across the reach. This makes math much simpler.
    transposed = []
    for field_count in range(len(reach[0])):
        this_field = []
        for seg_count in range(len(reach)):
            this_field.append(reach[seg_count][field_count])
        transposed.append(this_field)
    return transposed


def categorize_short(reach_list, fields):

    # Populates the THRESHOLD field
    # Below: The segment is lower than the given length threshold
    # Above: The segment is higher than the given length threshold

    length_index = fields.index("""CLIP_LEN""")
    for reach in reach_list:
        for seg in reach:
            if seg[length_index] <= length_cutoff:
                seg.append("Below")
            else:
                seg.append("Above")
    return reach_list


def categorize_type(reach_list, fields):

    # Populates the TYPE field
    short_index = fields.index("""THRESHOLD""")
    # Loops for each reach in the list
    for reach in reach_list:
        short_list = []
        # Adds the THRESHOLD values for this reach into list
        for seg_count in range(len(reach)):
            short_list.append(reach[seg_count][short_index])
        # Calculates the reach TYPE based off of the reach's THRESHOLD values
        extraction_type = parse_short_list(short_list)
        # Add the TYPE field values into the reach
        for seg in reach:
            seg.append(extraction_type)

    # Return a list of reaches, now with the TYPE field populated
    return reach_list


def categorize_action(reach_list, fields):

    # Categorizes the ACTION and MATH Field
    # Keep: Keep this segment for calculations
    # Delete: Delete this segment before calculations

    short_index = fields.index("""THRESHOLD""")
    type_index = fields.index("""TYPE""")
    for reach in reach_list:
        for seg in reach:
            seg_type = seg[type_index]
            seg_short = seg[short_index]

            if seg_type == "All" or seg_type == "None":
                action = "Keep"
                math = "Yes"
            elif seg_type == "Multiple":
                if seg_short == "Above":
                    action = "Keep"
                    math = "Yes"
                else:
                    action = "Delete"
                    math = "No"
            else:
                if seg_short == "Above":
                    action = "Keep"
                    math = "No"
                else:
                    action = "Delete"
                    math = "No"

            seg.append(action)
            seg.append(math)

    return reach_list


def parse_short_list(short_list):

    # Parses a reach by how many segments are under the length threshold
    # All: All segments are above the threshold
    # Multiple: Multiple, but not all segments are above the threshold
    # Single: A single segment is above the threshold
    # None: No segments are above the threshold

    if len(short_list) <= 2:
        if "Below" not in short_list:
            return "All"
        elif "Above" in short_list:
            return "Single"
        else:
            return "None"
    else:
        if "Above" not in short_list:
            return "None"
        elif "Below" not in short_list:
            return "All"
        a_count = short_list.count("Above")
        if a_count == 1:
            return "Single"
        else:
            return "Multiple"


def delete_unnecessary(reach_list):

    delete_list = []

    # Create a list of every segment that needs to be deleted
    for reach_index, reach in enumerate(reach_list):
        for seg_index, seg in enumerate(reach):
            if "Delete" in seg:
                delete_list.append([reach_index, seg_index])

    # Reverse the list so that indexes don't get ruined as we delete
    delete_list.reverse()

    # Delete all lists that has 'Delete' as their action
    for index in delete_list:
        reach = index[0]
        seg = index[1]
        reach_list[reach].pop(seg)

    return reach_list


def condense_to_single(reach_list, fields):

    length_index = fields.index("""CLIP_LEN""")

    new_return = []

    # Condenses each reach into a single segment with all averaged values
    for reach in reach_list:

        # This checks if we actually need to do any math
        if "Single" not in reach[0]:

            condensed_seg = [[]]

            # This will loop to do the calculations for each field
            for field_index in range(len(fields)):

                this_field = []
                length_list = []

                # This loops to fill the this_field list with the each value in that field for this reach
                # Also populates the length_list, which holds the lengths for each segment.
                for seg_index in range(len(reach)):

                    this_field.append(reach[seg_index][field_index])
                    length_list.append(reach[seg_index][length_index])

                # Condenses the current field into one value, adds it to the list for the current reach
                condensed_seg[0].append(parse_multi_seg(this_field, length_list))

            # Adds the reach, now only one set of values, to the larger return list
            new_return.append(condensed_seg)

        # Since it is the only good segment it its reach, we can just use these values directly
        else:
            new_return.append(reach)

    # Return a list of reaches, all with a single set of values
    return new_return


def parse_multi_seg(to_parse, length_list):

    # This checks to see if everything it was handed to parse is the same
    if len(set(to_parse)) == 1:
        # Every segment is the same in this field, so just return the first one
        return to_parse[0]

    # This checks to see if the field that is being parsed is a string
    elif isinstance(to_parse[0], str) or isinstance(to_parse[0], unicode):
        # Return the string from the longest segment, as that has the most influence
        max_index = length_list.index(max(length_list))
        return to_parse[max_index]

    # This checks to see if the field that is being parsed is a number
    elif isinstance(to_parse[0], int) or isinstance(to_parse[0], float):
        return weighted_average(to_parse, length_list)

    # This shouldn't ever really happen.
    else:
        return to_parse[0]


def weighted_average(to_parse, length_list):

    # Converts everything to floats
    to_parse = [float(s) for s in to_parse]
    length_list = [float(s) for s in length_list]

    # Remove negative values
    new_values = [value for value in to_parse if value > 0]
    new_lengths = []
    for keep in new_values:
        new_lengths.append(length_list[to_parse.index(keep)])

    if len(new_lengths) > 1:

        # Calculates the relative weight of each segment, based on its proportion of the total PIBO reach length
        weight_list = []
        for length in new_lengths:
            weight_list.append(length/sum(new_lengths))

        # Multiplies the weights by their values for each segment
        sum_list = []
        for data_value, weight in zip(new_values, weight_list):
            sum_list.append(data_value*weight)

        # Returns the final weighted average for the segment
        return sum(sum_list)

    else:
        # Return the value from the longest segment
        return to_parse[length_list.index(max(length_list))]


def cleanup(reach_list):

    # Changes list format from reaches containing a single segment to just a list of reaches
    cleaned_list = []
    for reach in reach_list:
        cleaned_list.append(reach[0])

    # Removes the THRESHOLD and ACTION fields from the list entirely
    for reach in cleaned_list:
        reach.pop(-2)
        reach.pop(-3)

    return cleaned_list


if __name__ == "__main__":
    main()
