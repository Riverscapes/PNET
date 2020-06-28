---
title: Step 1
weight: 1
---

The first step in PNET is to organize all of the initial inputs into the right folder structure, and prepare data for further processing. The inputs for this tool are:

- **Bottom of Reach field points (BOR)**
- These points represent the bottom of reaches from the field. No data needs to be on these points, other than a Site ID # [SiteID], Reach ID # [RchID], and year field [yr]. These represent all of the spatially explicit data from the field, so these points are crucial to getting spatially explicit reaches.
  
- **Top of Reach field points (TOR)**
  - These points represent the topof reaches from the field. No data needs to be on these points, other than a Site ID # [SiteID], Reach ID # [RchID], and year field [yr]. These represent all of the spatially explicit data from the field, so these points are crucial to getting spatially explicit reaches.

- **A shapefile with the boundaries of every watershed**
  - There must be a field called NAME, which holds the unique name for each watershed. 
  - This tool will run all analyses on each watershed individually, as well as for the entire project as well.

- **A shapefile with the stream network for the whole project**
  - This polyline shapefile represents the stream network that will be used to create field reaches. Field reaches are created by snapping TOR and BOR points to this stream network, then connecting both points using the stream network (in a later step)
  - This stream network does not require any data to be in the attribute table
  - All data networks being input in later steps also need to match the shape of this network. The networks do not need to be segmented in the same way.

- **The folder where the new folder structure will be created (Root Folder)**
  - This folder will be referred to as Root Folder or Project Folder in the future

- **A target data year**
  - For multiple reaches within a single site, field points with a year field closest to the target year will be prioritized. This value should be set to the year that represents what year the data networks used when they were run.

To begin, the watershed shapefile is queried to retrieve a list of every watershed’s name. For this step to work properly there must be a field distinguishing each watershed, called NAME. A series of folders is then created inside the Root Folder. There is one folder for each watershed, each using the name from the NAME field. A Projectwide Folder is created, with the prefix "00_". Folders with this prefeix are ignored except in special cases. Folders needed to hold data for the next few steps are created as well, and placed into each folder. 

To prepare the TOR and BOR field points for snapping, this step also clips the project-wide TOR and BOR field points by each watershed’s boundary and saves that into the respective watershed’s folder. The stream network is also clipped by the watershed’s boundary. 

Next, a single TOR point and BOR point is selected for each site. In the case of PIBO, each site has many different entries for different years of data collection. Each of these entries has a unique RchID. To decide which reach within the site should be used for further processing, we find the reach whose collection year is closest to the Data Year provided by the user.

Finally, this step also saves a shapefile containing all TOR field points, as well as a shapefile containing all BOR field points into a project-wide folder. All PNET scripts will save a project wide version of their outputs (if applicable).