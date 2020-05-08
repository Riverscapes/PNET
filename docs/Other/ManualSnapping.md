---
title: Point Snapping
weight: 1
---

Because of the snapping threshold established in Step 2, not all field points will be snapped onto the stream network. If preserving as many of these points as possible is your goal, unsnapped points van be fixed and reincorporated into the project.

To do this, first find the shapefiles "To_Fix_BOR.shp" and "To_Fix_TOR.shp". These are located in "00_Projectwide/Intermediates/Points/Unsnapped_Fixed". Put these two shapefiles into a blank ArcMap project, along with your original stream network file.

Start an editing session from the editor toolbar. Open the attribute table for the TOR points shapefile. Select the first point and zoom to it [CTRL+SHIFT+=]. Use your best judgement to determine if the point should be snapped to the network or deleted.

Make sure that snapping is enabled using the snapping toolbar.



**Should it be snapped?**

- Points should be snapped if you can reasonably assume that the stream the point is closest too was the same stream where field data was collected. You can reasonably assume this if the points are only slightly above the threshold established, or if there seem to be no other streams in the area. You can also check if the stream names are the same between the points and the stream shapefile (only if that data is available).

- The point should not be snapped if there is no obvious stream to which it belongs. This can happen in many scenarios. You should probably delete the point if there are no nearby streams, or if there are so many streams you don't feel confident placing it on any of them. This is entirely at the discretion of the user.

  

Repeat these steps for every TOR and BOR point, until they are all either snapped to the network or deleted. Make sure your edits are saved, then that's it! Don't change their names. All that remains is to make sure that the "Were Unsnapped Points Fixed?" box is checked in step 3.

