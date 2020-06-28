---
title: Step 2
weight: 2
---

The second step in PNET is to take all field points and snap them to the stream network. The inputs for this tool are:

- **Project Folder**
  - This is the folder that contains all data for the project. Folders with the prefix "00_" will be ignored.
- **Use Threshold?**
  - True: Points will stop trying to snap after a certain distance. Use this if you want to make sure points aren't snapping from too far away. This also makes the tool run faster
  - False: Use this if you want all points to snap to the network regardless of distance. Only use this if you have extreme confidence that all of your points are valid and close to the network. 
- **Threshold Range**
  -  A distance in meters that determines the aforementioned threshold. 

To begin, the tool retrieves stream networks for each watershed, and saves them into their appropriate folder. Another field is added to denote at what snapping distance the field point snapped. If the point is not snapped, a value of 999 is given.

This tool first attempts to snap every field point to the stream network, with a snapping distance of ten meters. If the field points are within that range, they are snapped to the network and the field denoting their snap distance is updated. The range of the snapping is increased by 10m, and snapping is performed again. This process continues until the snapping distance goes above the threshold (in which case all unsnapped points are given a snapping distance value of 999) or all points are snapped. If the user decides to not use the threshold, the points will continue snapping until they are all snapped, no matter the distance. 

X and Y location data are then added to the points. Finally, the points are saved into their respective folders, as well as merged into two project-wide shapefiles containing all TOR and BOR field points. A separate shapefile is saved for unsnapped and snapped points.