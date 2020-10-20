# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
import json
import urllib
import boto3
import logging
import base64
import time
import os
import requests
import random
import uuid
from datetime import datetime, timedelta
from aws_embedded_metrics import metric_scope
from PIL import Image
from io import BytesIO
from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.core import patch_all

patch_all()

S3Bucket = os.getenv('Bucket')

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client('s3')
rek = boto3.client('rekognition')
comprehend = boto3.client('comprehend')
firehose = boto3.client('firehose')
ssm = boto3.client('ssm')

male_names = ["Michael","Patrick","Stefan","Daniel","Thomas","Christoph","Dominik","Lukas","Philip","Florian","Manuel","Andreas","Alexander","Markus","Martin","Matthias","Christian","Mario","Bernhard","Johannes","Maximilian","Benjamin","Raphael","Peter","Christopher","René","Simon","Marco","Fabian","Julian","Marcel","Georg","Jakob","Tobias","Clemens","Robert","Oliver","Paul","Jürgen","Wolfgang","Felix","Josef","Hannes","Roman","Gerald","Sascha","Franz","Klaus","Pascal","Roland","Richard","Gregor","Harald","Gerhard","Armin","Gabriel","Marc","Alex","Alexis","Antonio","Austin","Beau","Beckett","Bentley","Brayden","Bryce","Caden","Caleb","Camden","Cameron","Carter","Casey","Cash","Charles","Charlie","Chase","Clark","Cohen","Connor","Cooper","David","Dawson","Declan","Dominic","Drake","Drew","Dylan","Edward","Eli","Elijah","Elliot","Emerson","Emmett","Ethan","Evan","Ezra","Felix","Gage","Gavin","Gus","Harrison","Hayden","Henry","Hudson","Hunter","Isaac","Jace","Jack","Jackson","Jacob","James","Jase","Jayden","John","Jonah","Joseph","Kai","Kaiden","Kingston","Levi","Liam","Logan","Lucas","Luke","Marcus","Mason","Matthew","Morgan","Nate","Nathan","Noah","Nolan","Oliver","Owen","Parker","Raphaël","Riley","Ryan","Samuel","Sebastian","Seth","Simon","Tanner","Taylor","Theo","Tristan","Turner","Ty","William","Wyatt"]
female_names = ["Julia","Lisa","Stefanie","Katharina","Melanie","Christina","Sabrina","Sarah","Anna","Sandra","Katrin","Carina","Bianca","Nicole","Jasmin","Kerstin","Tanja","Jennifer","Verena","Daniela","Theresa","Viktoria","Elisabeth","Nadine","Nina","Tamara","Madalena","Claudia","Jacquelina","Machaela","Martina","Denise","Barbara","Bettina","Alexandra","Cornelia","Maria","Vanessa","Andrea","Johanna","Eva","Natalie","Sabine","Isabella","Anja","Simone","Janine","Marlene","Patricia","Petra","Laura","Yvonne","Manuela","Karin","Birgit","Caroline","Tine","Carmen","Abigail","Adalyn","Aleah","Alexa","Alexis","Alice","Alyson","Amelia","Amy","Anabelle","Anna","Annie","Aria","Aubree","Ava","Ayla","Brielle","Brooke","Brooklyn","Callie","Camille","Casey","Charlie","Charlotte","Chloe","Claire","Danica","Elizabeth","Ella","Ellie","Elly","Emersyn","Emily","Emma","Evelyn","Felicity","Fiona","Florence","Georgia","Hailey","Haley","Isla","Jessica","Jordyn","Juliette","Kate","Katherine","Kayla","Keira","Kinsley","Kyleigh","Lauren","Layla","Lea","Leah","Lexi","Lily","Lydia","Lylah","Léa","Macie","Mackenzie","Madelyn","Madison","Maggie","Marley","Mary","Maya","Meredith","Mila","Molly","Mya","Olivia","Paige","Paisley","Peyton","Piper","Quinn","Rebekah","Rosalie","Ruby","Sadie","Samantha","Savannah","Scarlett","Selena","Serena","Sofia","Sophia","Sophie","Stella","Summer","Taylor","Tessa","Victoria","Violet","Zoey","Zoé"]
surnames = ["Silva","Lopez","Rodrigues","Jones","Martinez","Hernandez","Abbot","Ross","Pitt","Foster","Gruber","Huber","Bauer","Wagner","Müller","Pichler","Steiner","Moser","Mayer","Hofer","Leitner","Berger","Fuchs","Eder","Fischer","Schmid","Winkler","Weber","Schwarz","Maier","Schneider","Reiter","Mayr","Schmidt","Wimmer","Egger","Brunner","Lang","Baumgartner","Auer","Binder","Lechner","Wolf","Novak","Wallner","Aigner","Ebner","Koller","Lehner","Haas","Schuster","Anderson","Bergeron","Bouchard","Boucher","Butler","Santiago","Cruz","Brown","Bélanger","Campbell","Chan","Clark","Cote","Fortin","Gagnon","Gagné","Gauthier","Chu","Yong","Girard","Johnson","Jones","Lam","Lavoie","Lavoie","Leblanc","Lee","Li","Lévesque","Martin","Morin","Ortega","Ouellet","Paquette","Patel","Pelletier","Roy","Simard","Smith","Taylor","Thompson","Tremblay","White","Williams","Wilson","Wong"]

def GetDominantLanguage(tweet_text):
    language = "en"
    score = 0
    try:                
        if len(tweet_text) > 25:
            response = comprehend.detect_dominant_language(
                Text=tweet_text
            )
            for l in response["Languages"]:
                lcode = l["LanguageCode"]
                lscore = l["Score"]
                if lscore > score:
                    score = lscore
                    language = lcode
            
            return language

        else:
            return language

    except Exception as e:
        logger.error('Something went wrong: ' + str(e))
        return language

def GetSentiment(tweet_text, language_code):
    try:
        response = comprehend.detect_sentiment(
            Text=tweet_text,
            LanguageCode=language_code
        )

        return response["Sentiment"]

    except Exception as e:
        logger.error('Something went wrong: ' + str(e))
        return 'Unknow'


def GetSsmParam(paramKey, isEncrypted):
    try:
        ssmResult = ssm.get_parameter(
            Name=paramKey,
            WithDecryption=isEncrypted
        )

        if (ssmResult["ResponseMetadata"]["HTTPStatusCode"] == 200):
            return ssmResult["Parameter"]["Value"]
        else:
            return ""

    except Exception as e:
        logger.error(str(e))
        return ""

    
@metric_scope
def handler(event, context, metrics):
    try:
        if "result" in event:
            if event["result"] == "Moderated":
                logger.warning(event["msg"])
                return {'result': 'Moderated' }


        # If Firehose is implemented get its name
        FireHoseName = GetSsmParam('/twitter-demo/deliverystream', False)           

        faces_count = 0
        low_res_count = 0
        face_not_identified_count = 0
        faces = []
        fdata = {}
        event_data = json.loads(event["data"])
        identified_faces = event_data["facerecords"]
        fdata["first_name"] = 'NULL'
        fdata["last_name"] = 'NULL'

        for face in identified_faces:                     
            if (int(face["Confidence"])) < 80:
                face_not_identified_count = face_not_identified_count + 1
                continue

            face_id = str(uuid.uuid4())
            logger.info('## FaceId: ' + face_id)
            xray_recorder.begin_subsegment('## FaceId: ' + face_id)
            
            if str(face["Gender"]["Value"]).lower() == "male":
                fdata["first_name"] = random.choice(male_names)
            else:
                fdata["first_name"] = random.choice(female_names)

            language = GetDominantLanguage(event_data["full_text"])
            sentiment = GetSentiment(event_data["full_text"],language)
            
            fdata["sentiment"] = sentiment
                
            fdata["last_name"] = random.choice(surnames)
            
            fdata["image_url"] = event_data["image_url"]
            fdata["full_text"] = event_data["full_text"]
            fdata["tweet_id"] = event_data["tweet_id"]
            fdata["gender"] = face["Gender"]
            fdata["face_id"] = face_id
            fdata["emotions"] = face["Emotions"]            
            fdata["agerange"] = face["AgeRange"]

            # calculate the bounding boxes the detected face 
            r = requests.get(event_data["image_url"], allow_redirects=True)
            stream = BytesIO(r.content)
            image = Image.open(stream)
            imgWidth, imgHeight = image.size 
            box = face["BoundingBox"]
            left = imgWidth * box['Left']
            top = imgHeight * box['Top']
            width = imgWidth * box['Width']
            height = imgHeight * box['Height']

            fdata["bbox_left"] = left
            fdata["bbox_top"] = top
            fdata["bbox_width"] = width
            fdata["bbox_height"] = height 
            fdata["imgWidth"] = imgWidth 
            fdata["imgHeight"] = imgHeight
            fdata["updated_at"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")

            faces_count = faces_count + 1
            faces.append(face_id)

            if imgWidth < 500:
                low_res_count = low_res_count + 1
                # logger.warning("Image width not greater than 500px. Not processing.")
                continue

            if len(event_data) > 2:
                file_name = face_id + '.json'
                key = "data/json-records/" + file_name  
                logger.info(fdata)
                s3.put_object(
                    ACL='private',
                    Body=json.dumps(fdata),
                    Bucket=S3Bucket,          
                    Key=key
                )        

                if len(FireHoseName) > 2:
                    response = firehose.put_record(
                        DeliveryStreamName=FireHoseName,
                        Record={
                            'Data': json.dumps(fdata)
                        }
                    )  
                        
                xray_recorder.end_subsegment()
        
        if (len(identified_faces) > 0):
            metrics.set_namespace('TwitterRekognition')
            metrics.put_metric("FacesProcessed", faces_count, "Count")
            metrics.set_property("RequestId", context.aws_request_id)            
            metrics.set_property(
                "payload", { "processed": faces_count, "low_res": low_res_count, "face_not_identified_count": face_not_identified_count }
            )

        return { 'result': 'Succeed', 'count': str(faces_count) }

    except Exception as e:
        logger.error(str(e))
        return {'result': 'Fail', 'msg': str(e) }