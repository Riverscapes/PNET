library(car)
library(MASS)

# Clean workspace
rm(list = ls())


      # THIS IS THE ONLY PART YOU NEED TO EDIT

      # Put your project_folder here (Make sure to do double slashes like this: \\)
      project_folder = "C:\\Users\\Tyler\\Desktop\\Work\\FullRun"
      # Put your comparison fields csv here (Make sure to do double slashes like this: \\)
      field_info_csv = "C:\\Users\\Tyler\\Desktop\\Work\\PNET_Fields_Master.csv"

      
# Get PNET data
all_data_location = "\\00_Projectwide\\Outputs\\Comparisons\\Numerical\\Numerical_Comparison_Data.csv"
all_data = read.csv(paste(project_folder, all_data_location, sep = ""))
fields =read.csv(field_info_csv, fileEncoding="UTF-8-BOM")
export_list = list()


save_loc_csv = "\\00_Projectwide\\Outputs\\Comparisons\\Numerical\\Outliers.csv"
save_loc = paste(project_folder, save_loc_csv, sep = "")
#Check its existence
if (file.exists(save_loc)) 
  #Delete file if it exists
  file.remove(save_loc)


for (row in 1:nrow(fields)){

  new_name = lapply((fields[row, "Name"]), as.character)[[1]]
  pnet_valid = lapply((fields[row, "PNET_Valid"]), as.character)[[1]]
  field_valid = lapply((fields[row, "Field_Valid"]), as.character)[[1]]
  pnet_mod = "pn_"
  field_mod = "fd_"
  pnet_field = paste(pnet_mod, strtrim(new_name, 7),sep = "")
  field_field = paste(field_mod, strtrim(new_name, 7),sep = "")
  
  analysis = all_data[, c("RchID", pnet_field, field_field)]
  
  #Remove invalid data
  if (pnet_valid == "Y"){
    analysis_new = analysis[ analysis[[pnet_field]] >= 0 , ]
  }
  else{
    analysis_new = analysis[ analysis[[pnet_field]] > 0 , ]
  }

  if (field_valid == "Y"){
    analysis = analysis_new[ analysis_new[[pnet_field]] >= 0 , ]
  }
  else{
    analysis = analysis_new[ analysis_new[[pnet_field]] > 0 , ]
  }
  
  fit <- lm(analysis[,2]~analysis[,3]) 
  fit_res = studres(fit)
  fit_res_df = cbind(read.table(text = names(fit_res)), fit_res)
  new_data = cbind(analysis, fit_res_df)
  outliers = new_data[abs(new_data$fit_res) > 2,]
  outlier_id = outliers$RchID
  
  export_list[[pnet_field]] = outlier_id
  export_list[[field_field]] = outlier_id

  
  write.table(export_list[pnet_field], save_loc  , append= T, sep=',' )
}


