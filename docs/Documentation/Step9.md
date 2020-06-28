---
title: Step 9
weight: 9
---

The ninth step in PNET is to make comparisons between the field database and PNET data (from previously entered data networks). The inputs for this tool are:



- Root Folder

- A CSV containing all data gathered in the field (field database)

- A list of fields already in PNET that have direct comparisons in the field database

- A list of fields in the field database that have direct comparisons to PNET fields

- A list of what you want the new fields to be referred to (A label for both fields)

  

  To begin, this tool retrieves data from the field database, and saves it to each watershed. Looking at only the fields indicated by the user, comparisons between PNET and the field database are made. Four new field are added for comparison purposes:

**pnet_(field):** This is the data from the models previously put in PNET (BRAT, RCAT, etc.)

**fld_(field):** This is the data from field measurements (PIBO)

**dif_(field):** This is the result of taking pnet-fld

**pdif_(field):** This is the percent difference between the two data ((max-min)/max)

The comparison data is then saved to a CSV, and onto a shapefile containing all field points. A plot is also created that plots input data models on one axis, and field measured data on the other axis.