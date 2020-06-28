---
title: Step 10
weight: 10
---

The tenth step in PNET is to make categorical comparisons between the field database and PNET data (from previously entered data networks). The inputs for this tool are:



- **Project Folder**

  - This is the folder that contains all data for the project. Folders with the prefix "00_" will be ignored.

- **Fields List**

  - A CSV with data about what comparisons need to be performed. More detail can be found in the "Other" section

  

To begin, this tool retrieves categorical data from the field database, and saves it to each watershed. Looking at only the fields indicated by the user, comparisons between PNET and the field database are made.

Every metagroup will be split into all of its unique categories. Each of these unique categories will have a folder of their own for plots. For instance, if our metagroup field was [CONDITION], folders called GOOD, FAIR, and POOR would be created.

Within each metagroup (or normally, if there is no metagroup), each unique value within the group is graphed against a variety of variables. So, if our group field was [SLOPE_CLASS], each graph would have HIGH, MODERATE, and LOW on their x axis, as categories for the box plot. The Y axis for the graphs is determined from the fields list CSV.

