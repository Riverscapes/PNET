---
title: Step 1
weight: 1
---

The first step in PNET is to organize all of the initial inputs into the right folder structure. The inputs for this tool are:



- Bottom of Reach field points (BOR) 

- Top of Reach field points (TOR)

- A shapefile with the boundaries of every watershed

- A shapefile with the stream network for the whole project

- The folder where the new folder structure will be created (Root Folder)

  

To begin, the watershed shapefile is queried to retrieve a list of every watershed’s name. For this step to work properly there must be a field called NAME. A series of folders is then created inside the Root Folder. There is one folder for each watershed, each using the name from the NAME field. Folders needed to hold data for the next few steps are created as well, and placed into each folder. 

To prepare the TOR and BOR field points for snapping, this step also clips the project-wide TOR and BOR field points by each watershed’s boundary and saves that into the watershed’s folder. The stream network is also clipped by the watershed’s boundary. This step also removes all field points that have identical reach IDs. Finally, this step also saves a shapefile containing all TOR field points, as well as a shapefile containing all BOR field points into a project-wide folder. All PNET scripts will save a project wide version of their outputs (if applicable).