CREATE EXTERNAL TABLE `twitter_data`.`json_records`(
    `first_name` string COMMENT 'from deserializer', 
    `last_name` string COMMENT 'from deserializer', 
    `image_url` string COMMENT 'from deserializer', 
    `guidstr` string COMMENT 'from deserializer', 
    `gender` struct<value:string,confidence:double> COMMENT 'from deserializer', 
    `face_id` string COMMENT 'from deserializer', 
    `emotions` array<struct<type:string,confidence:double>> COMMENT 'from deserializer', 
    `bbox_left` double COMMENT 'from deserializer', 
    `bbox_top` double COMMENT 'from deserializer', 
    `bbox_width` double COMMENT 'from deserializer', 
    `bbox_height` double COMMENT 'from deserializer', 
    `imgWidth` int COMMENT 'from deserializer', 
    `imgHeight` int COMMENT 'from deserializer', 
    `full_text` string COMMENT 'from deserializer', 
    `sentiment` string COMMENT 'from deserializer', 
    `updated_at` string COMMENT 'from deserializer', 
    `agerange` struct<low:int,high:int> COMMENT 'from deserializer')
    ROW FORMAT SERDE 
      'org.openx.data.jsonserde.JsonSerDe' 
    WITH SERDEPROPERTIES ( 
      'paths'='agerange,box,emotions,face_id,first_name,gender,guidstr,image_url,last_name') 
    STORED AS INPUTFORMAT 
      'org.apache.hadoop.mapred.TextInputFormat' 
    OUTPUTFORMAT 
      'org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat'
    LOCATION
      's3://<app-bucket>/json-records/'
    TBLPROPERTIES ('has_encrypted_data'='false');