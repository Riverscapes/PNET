---
title: Step 7
weight: 7
---

The seventh step in PNET is to extract data from data networks onto the field points and field reaches. The inputs for this tool are:



- Root Folder
- A length cutoff. All segments below this length in meters will not be considered when calculating weighted averages for multi segment reaches.



  This step is the longest, and also most important step in PNET. All of the calculations happen once per data network, per watershed. The first action is to clip the data network by the field reaches. Now we have data reaches that are exactly as long as the field reaches. The data reaches are still segmented. The fact that the data reaches are segmented is important for data extraction. A field is added to each data network segment that indicates how long that segment is. The length of each clipped segment relative to the total length of the field reach is used as the weight for the weighted average later.

  Extracting data network data to points is easy. A spatial join is performed on the points and data network, and the point adopts the data of whatever data network segment was closest to it. Some unnecessary fields are removed from the field points, then they are all saved into the appropriate folder. One output is saved per data network per watershed. 

  Then the data network’s information is extrapolated onto each field reach. The first step is to separate each field reach into two categories: field reaches that only overlap a single data network segment, and field reaches that overlap multiple data network segments. The field reaches that only overlap one are treated just like the field points, and a one to one spatial join is performed to extract the data onto the field reaches. For all other field reaches, a spatial join is performed with the data network segments to get a count of how many data network segments each field reach overlaps.

  First, each data network segment within a field reach is tagged as either above or below the threshold. This threshold exists because many models don’t have valuable data for segments that are below a certain length. After that, each reach is tagged with an extraction type (Single, Multiple, All, or None). 



**Single**: If only one of the segments in the reach is above the threshold, no extraction math needs to be done and it can be treated like a field reach that only contains one data network segment. 

**Multiple**: If multiple data segments, but not all segments are above the threshold, it is tagged as Multiple. This means that any segments below the threshold will be removed from calculations, but the remaining segments will be extracted using weighted means.

  **All**: If all data network segments in this field reach are above the threshold, they will all be extracted using weighted means.

**None**: If no data network segments in this field reach are above the threshold, they will all be extracted using weighted means. This is because below this threshold, making judgements about which data network segment has more accurate data is difficult. Luckily this type of field reach is extremely rare and most likely won’t happen over the entire project.



Once each reach has been appropriately tagged, and unnecessary data network segments have been removed, the final step is to extract the remaining data using weighted means. For every field in the data network, there are two possibilities:



**Text**: If the data in this field is text, then the only data that is extracted onto the field reach is the value of this field in the longest (m) data network segment.

**Numeric**: If the data is numeric, a weighted average is taken, using the length of each data network segment as the weight. We can assume that the longest data network segment contains the most representative data for the entire field reach, and the degree to which the data network segment is representative decreases with relative length to the field reach.

  

  Finally, all of the field reaches are merged back together and output into their own shapefile, one per data network per watershed. A field is also added to indicate what extraction type the field reach used, and if any weighted averaging was performed. 