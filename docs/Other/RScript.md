---
title: Outlier Finder Script
weight: 2
---

This script will find outliers and create a CSV full of outlier data that step 9b can understand. Run this between steps 9a and 9b. There are only three inputs that need to be changed

- **Project Folder**
  - This is the folder that contains all data for the project. Folders with the prefix "00_" will be ignored. Remember to put the entire filepath, and use double slashes \\\\.
- **Field Info CSV** 
  - This is the CSV with the list of all fields that you wan to compare. Be careful to keep the names of the columns the same as the template
- **Cook Threshold**
  - The threshold that determines what is or is not an outlier. Any cook's distance value above this will be considered an outlier.

Open this script up in R Studio. Replace the parameters to fit your folder structure, select all of the code, then hit run. 

For every comparison, this script creates a regression, and finds the reach with the highest cook's value for that regression. If that cook's value is above the threshold, it removes it from the regression. This repeats until no cook's distances are above the threshold.

Summary statistics are also printed into the R Console.