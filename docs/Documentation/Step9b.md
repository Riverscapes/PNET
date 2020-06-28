---
title: Step 9b
weight: 9
---

Before this step is run, you  need to run the Outlier Finder script in R. This will identify outliers and save a list of outliers that this tool can understand. This tool simply removes those outliers

- **Project Folder**
  
  - This is the folder that contains all data for the project. Folders with the prefix "00_" will be ignored.
  
- **Fields List**

  - A CSV with data about what comparisons need to be performed. More detail can be found in the "Other" section

  

This tool plots every comparison between variables. For any given comparison, here is the process that takes place

1. Outliers are removed from the dataset. It is important to note that outliers are never removed from any of the CSVs or Shapefiles, only immediately before being plotted
2. Negative values are removed
3. If zeroes are marked as invalid, then they are also removed from the dataset, either for the PNET field and/or the field collected field
4. A regression is created for the remaining data, calculating the R2 value
5. Data is plotted, and saved within the Comparisons/Numerical folder.

