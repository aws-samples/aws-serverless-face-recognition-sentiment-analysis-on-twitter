CREATE EXTERNAL TABLE `parquet_records`(
  `first_name` string, 
  `last_name` string, 
  `image_url` string, 
  `guidstr` string, 
  `gender` struct<value:string,confidence:double>, 
  `face_id` string, 
  `emotions` array<struct<type:string,confidence:double>>, 
  `bbox_left` double, 
  `bbox_top` double, 
  `bbox_width` double, 
  `bbox_height` double, 
  `imgwidth` int, 
  `imgheight` int, 
  `full_text` string, 
  `sentiment` string, 
  `updated_at` string, 
  `agerange` struct<low:int,high:int>)
ROW FORMAT SERDE 
  'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe' 
STORED AS INPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat' 
OUTPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat'
LOCATION
  's3://<app-bucket>/parquet-yyyy/'
TBLPROPERTIES ('has_encrypted_data'='false',
'classification'='parquet', 
'compressionType'='none');