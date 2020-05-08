---
title: Step 3
weight: 3
---

The third step in PNET is to prepare the field points for the reach editing step. The inputs for this tool are:

- Project Folder
  - This is the folder that contains all data for the project. Folders with the prefix "00_" will be ignored.
- Were Unsnapped Points Fixed?
  - Check this if you manually edited unsnapped points to be snapped in the step before this. Those manually edited points will be reincorporated into the project.

Before this step the user may edit all of the unsnapped points found in 00_ProjectWide\Intermediates\Points\Unsnapped_Fixed so that they are snapped to the network. This step is optional, and is detailed more in a later portion of this text. If the user did edit these points, set the “Were Unsnapped Points Fixed” parameter to true. If the user decides to skip this step, set the parameter to false. 

If that parameter is true, all of the fixed points for the project are saved to their correct folders. A field is added to all field points that indicates whether they are TOR or BOR. They are then merged into one shapefile. The stream network is then dissolved so that it creates a continuous, unbroken line. That line is then split at every field point. This should create a single continuous line that represents each field reach, although there will also be lots of extra lines, which will be removed in the next step. All of the outputs are saved into the “Reach_Editing/Inputs” folder.