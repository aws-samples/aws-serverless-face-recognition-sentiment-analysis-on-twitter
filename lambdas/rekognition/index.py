# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
from datetime import datetime, timedelta
import json
import urllib
import boto3
import logging
import uuid
import urllib 
import io
import os
import requests
from time import sleep
from aws_embedded_metrics import metric_scope
from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.core import patch_all

patch_all()

S3Bucket = os.getenv('Bucket')

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client('s3')
s3_bucket = S3Bucket

rek = boto3.client('rekognition')

status = ["success", "error", "moderated"]
year_week = datetime.now().strftime("%Y-W%U")
year_month = datetime.now().strftime("%Y-%m")
    
@metric_scope
def handler(event, context, metrics):   
    """
    Lambda handler for face detection and content moderation using Amazon Rekognition.
    
    Updated to use latest AWS Rekognition API features:
    - Enhanced moderation labels with ContentTypes and TaxonomyLevel support
    - Expanded face attributes including EMOTIONS, EYE_DIRECTION, and FACE_OCCLUDED
    - Improved error handling and parameter validation
    """
    
    # Validate required input parameters
    if not event.get("image_url"):
        logger.error("Missing required parameter: image_url")
        return {'result': 'Fail', 'msg': 'Missing required parameter: image_url'}
    
    try:
        r = requests.get(event["image_url"], allow_redirects=True, timeout=10)
        r.raise_for_status()  # Raise exception for bad HTTP status codes
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to download image from URL: {str(e)}")
        return {'result': 'Fail', 'msg': f'Failed to download image: {str(e)}'}

    # Updated: Use specific attributes for better performance and to include new features
    # EMOTIONS: Provides emotion detection (happy, sad, angry, etc.)
    # EYE_DIRECTION: Provides gaze direction information (Pitch and Yaw angles)
    # FACE_OCCLUDED: Detects if face is partially covered/obscured
    # These are beneficial for sentiment analysis use case
    attributes = ["DEFAULT", "EMOTIONS", "EYE_DIRECTION", "FACE_OCCLUDED"]

    # CONTENT MODERATION API CALL
    # Updated: MinConfidence parameter is explicitly set (best practice)
    # Note: ProjectVersion parameter can be added for custom moderation adapters if needed
    retries = 0
    while (retries < 5):
        try:
            xray_recorder.begin_subsegment('## Moderation')
            mod_response = rek.detect_moderation_labels(
                Image={
                    'Bytes': r.content
                },
                MinConfidence=50  # Explicitly set minimum confidence threshold
                # ProjectVersion parameter can be added here for custom moderation models:
                # ProjectVersion='arn:aws:rekognition:region:account:project/project-name/version/version-name/timestamp'
            )
            xray_recorder.end_subsegment()
            break

        except rek.exceptions.InvalidParameterException as e:
            logger.error(f"Invalid parameter in moderation request: {str(e)}")
            return {'result': 'Fail', 'msg': f'Invalid moderation parameters: {str(e)}'}
        except rek.exceptions.ImageTooLargeException as e:
            logger.error(f"Image too large for moderation: {str(e)}")
            return {'result': 'Fail', 'msg': 'Image exceeds size limits'}
        except rek.exceptions.InvalidImageFormatException as e:
            logger.error(f"Invalid image format for moderation: {str(e)}")
            return {'result': 'Fail', 'msg': 'Invalid image format (must be JPEG or PNG)'}
        except rek.exceptions.ProvisionedThroughputExceededException as e:
            logger.error(f"Throughput exceeded for moderation: {str(e)}")
            retries = retries + 1
            logger.info("sleeps: " + str(pow(2, retries) * 0.15))
            sleep(pow(2, retries) * 0.15)            
            if retries == 5:
                logger.error("Error: Moderation backoff limit")
                return {'result': 'Fail', 'msg': str(e) + " Moderation backoff limit"} 
            else:
                continue
        except Exception as e:
            logger.error(f"Unexpected error in moderation: {str(e)}")                 
            retries = retries + 1
            logger.info("sleeps: " + str(pow(2, retries) * 0.15))
            sleep(pow(2, retries) * 0.15)            
            if retries == 5:
                logger.error("Error: Moderation backoff limit")
                return {'result': 'Fail', 'msg': str(e) + " Moderation backoff limit"} 
            else:
                continue

    # Updated: Process enhanced moderation response with new fields
    if len(mod_response.get("ModerationLabels", [])) != 0:
        metrics.set_namespace('XSentimentAnalysis')
        metrics.put_metric("ImagesModerated", 1, "Count")
        metrics.set_property("RequestId", context.aws_request_id)
        
        # Updated: Log enhanced moderation label information including TaxonomyLevel
        moderation_details = []
        for label in mod_response["ModerationLabels"]:
            label_info = {
                'Name': label.get('Name'),
                'Confidence': label.get('Confidence'),
                'ParentName': label.get('ParentName', ''),
                'TaxonomyLevel': label.get('TaxonomyLevel', 0)  # New field: hierarchical level (1-3)
            }
            moderation_details.append(label_info)
        
        metrics.set_property("Labels", moderation_details)
        
        # Updated: Log ContentTypes if present (indicates content type: animation, sports, game, etc.)
        if "ContentTypes" in mod_response:
            content_types = [
                {'Name': ct.get('Name'), 'Confidence': ct.get('Confidence')} 
                for ct in mod_response["ContentTypes"]
            ]
            metrics.set_property("ContentTypes", content_types)
            logger.info(f"Content types detected: {content_types}")
        
        # Log moderation model version for tracking
        if "ModerationModelVersion" in mod_response:
            logger.info(f"Moderation model version: {mod_response['ModerationModelVersion']}")
        
        return {'result': 'Moderated'}

    # FACE DETECTION API CALL
    # Updated: Using optimized attribute list with new features
    retries = 0
    while (retries < 5):
        try:
            xray_recorder.begin_subsegment('## DetectFaces')            
            rek_response = rek.detect_faces(
                Image={"Bytes": r.content},
                Attributes=attributes  # Now includes EMOTIONS, EYE_DIRECTION, FACE_OCCLUDED
            )
            xray_recorder.end_subsegment()
            break

        except rek.exceptions.InvalidParameterException as e:
            logger.error(f"Invalid parameter in face detection request: {str(e)}")
            return {'result': 'Fail', 'msg': f'Invalid face detection parameters: {str(e)}'}
        except rek.exceptions.ImageTooLargeException as e:
            logger.error(f"Image too large for face detection: {str(e)}")
            return {'result': 'Fail', 'msg': 'Image exceeds size limits'}
        except rek.exceptions.InvalidImageFormatException as e:
            logger.error(f"Invalid image format for face detection: {str(e)}")
            return {'result': 'Fail', 'msg': 'Invalid image format (must be JPEG or PNG)'}
        except rek.exceptions.ProvisionedThroughputExceededException as e:
            logger.error(f"Throughput exceeded for face detection: {str(e)}")
            retries = retries + 1
            logger.info("sleeps: " + str(pow(2, retries) * 0.15))
            sleep(pow(2, retries) * 0.15)
            if retries == 5:
                logger.error("Error: FaceDetect backoff limit")
                return {'result': 'Fail', 'msg': str(e) + " FaceDetect backoff limit"} 
            else:
                continue
        except Exception as e:
            logger.error(f"Unexpected error in face detection: {str(e)}")                 
            retries = retries + 1
            logger.info("sleeps: " + str(pow(2, retries) * 0.15))
            sleep(pow(2, retries) * 0.15)
            if retries == 5:
                logger.error("Error: FaceDetect backoff limit")
                return {'result': 'Fail', 'msg': str(e) + " FaceDetect backoff limit"} 
            else:
                continue

    logger.info("FaceDetails: " + str(len(rek_response.get("FaceDetails", []))))

    # Updated: Enhanced face data processing with new attributes
    if len(rek_response.get("FaceDetails", [])) > 0:
        hdata = {}
        hdata['image_url'] = str(event["image_url"])
        hdata['full_text'] = event.get('full_text', '')
        hdata['tweet_id'] = event.get("tweet_id", '')
        
        # Updated: FaceDetails now include Emotions, EyeDirection, and FaceOccluded attributes
        # These provide richer sentiment analysis capabilities:
        # - Emotions: array of emotion types with confidence scores (HAPPY, SAD, ANGRY, etc.)
        # - EyeDirection: Pitch and Yaw angles indicating gaze direction
        # - FaceOccluded: Boolean indicating if face is partially obscured
        hdata['facerecords'] = rek_response["FaceDetails"]
        
        # Log information about enhanced attributes for monitoring
        for idx, face in enumerate(rek_response["FaceDetails"]):
            if "Emotions" in face:
                emotions = [(e.get('Type'), e.get('Confidence')) for e in face.get('Emotions', [])]
                logger.info(f"Face {idx} emotions: {emotions}")
            if "EyeDirection" in face:
                eye_dir = face.get('EyeDirection', {})
                logger.info(f"Face {idx} eye direction - Pitch: {eye_dir.get('Pitch')}, Yaw: {eye_dir.get('Yaw')}")
            if "FaceOccluded" in face:
                occluded = face.get('FaceOccluded', {})
                logger.info(f"Face {idx} occluded: {occluded.get('Value')} (confidence: {occluded.get('Confidence')})")

        faces_count = len(rek_response["FaceDetails"])
        return {'result': 'Succeed', 'count': str(faces_count), 'data': json.dumps(hdata)}
        
    else:
        logger.error('Unable to rekognize any face')
        return {'result': 'Fail', 'msg': 'Unable to rekognize face'}