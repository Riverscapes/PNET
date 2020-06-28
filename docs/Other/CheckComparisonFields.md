---
title: Check Comparison Fields
weight: 2
---

This script is not polished, but can be helpful in saving you from headaches if you are working with hundreds of comparisons. If you decide to run this, it should be immediately after step 8.

- **Root Folder**
  - This is the folder that contains all data for the project. Folders with the prefix "00_" will be ignored.

- **Field Database**
  - A CSV containing all data collected in the field. This csv must have a [RchID] field

- **Fields List**
  - A CSV with data about what numerical comparisons need to be performed. More detail can be found in the "Other" section

All this step does is it runs through all of the fields that exists in your fields list csv, and makes sure they really exist in the dataset. This is great for checking to make sure all your data is there before you commit to the long run time of Step 9.

**If Your Field Is Missing**

There are many possible reasons this could happen. Check to make sure your field wasn't truncated in being entered into PNET. Fields can only have 10 characters. Also make sure to check cases, as fields are case sensitive in some situations. 

