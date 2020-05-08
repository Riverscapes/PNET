---
title: Step 9a
weight: 9
---

The ninth step in PNET is to make numerical comparisons between the field database and PNET data (from previously entered data networks). The inputs for this tool are:



- **Project Folder**

  - This is the folder that contains all data for the project. Folders with the prefix "00_" will be ignored.

- **Field Database**

  - A CSV containing all data collected in the field. THis csv must have a [RchID] field

- **Fields List**

  - A CSV with data about what numerical comparisons need to be performed. More detail can be found in the "Other" section

  

To begin, this tool retrieves data from the field database, and saves it to each watershed. Looking at only the fields indicated by the user, comparisons between PNET and the field database are made. Two new fields are added for comparison purposes:

**pn_(field):** This is the data from the models previously put in PNET (BRAT, RCAT, etc.)

**fd_(field):** This is the data from field measurements (PIBO)

The comparison data is then saved to a CSV, and onto a shapefile containing all field points.