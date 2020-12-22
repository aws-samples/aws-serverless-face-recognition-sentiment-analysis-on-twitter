#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from '@aws-cdk/core';
import { TwitterStack } from '../lib/twitter-stack';

const app = new cdk.App();
new TwitterStack(app, 'TwitterStack');

app.synth();