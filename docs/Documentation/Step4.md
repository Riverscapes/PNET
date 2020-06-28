---
title: Step 4
weight: 4
---

The fourth step in PNET is to create field reaches based on field points and the stream network. The inputs for this tool are:

- **Project Folder**
  - This is the folder that contains all data for the project. Folders with the prefix "00_" will be ignored.

To create field reaches, this tool looks at every stream network segment that touches a field point. It is important to note that as this point the stream network segments were created by splitting the stream network at each field point. A simple process is performed to determine which segments are field reaches, and which ones need to be deleted.

If the segment is not touching exactly two points (one TOR and one BOR from the same site), it is removed. Then, all field points that are touching field reaches are saved to the Reach Editing folder, along with the field reaches.