<template>
    <ProgressBar style="height: 6px;" v-if="loading" mode="indeterminate" />
    <Card style="width: 500;">
        <template #title> {{ emotion }} </template>
        <template #subtitle>  
            Score: {{ tweet.confidence }} <br />
            Tweet text Sentiment: {{ tweet.sentiment }}
        </template>
        
        <template #content>            
            <canvas
                :id="'canvas_' + emotion"
            />
            <div v-if="!loading">
                {{ tweet.first_name }} {{ tweet.last_name }} - Age {{ tweet.age }} - Updated at {{ tweet.updated_at }} <br />
                <Button icon="pi pi-eraser" text rounded size="small" severity="danger" aria-label="Delete" @click="delImage(tweet)" />
            </div>
        </template>        
    </Card>
</template>
  
  <script>
  // Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
  // SPDX-License-Identifier: MIT-0
  import axios from "axios";
  
  export default {
    data() {
      return {
          baseUrl: import.meta.env.VITE_API_URL,
          tweet: {},
          loading: true,
          error: false,
          errormsg: ""
      }
    },
    props: {
      emotion: null
    },
    async mounted() {
      try {
            await axios.get(this.baseUrl + "image?emotion=" + this.emotion).then(results => { 
            this.tweet = results.data
            this.loading = false
            this.renderImages(this.tweet);
          }); 
        } catch (error) {
          console.error(error);
          this.errormsg = error;
          this.error = true;
          this.loading = false;
        }            
    },
    methods: {
      renderImages(tweet) {
        try {
          let id = "canvas_" + tweet.etype;
          //console.log(id);
  
          let scale = 500 / tweet.imgWidth;
  
          let box_left = Math.round(tweet.bbox_left * scale);
          let box_top = Math.round(tweet.bbox_top * scale);
          let box_width = Math.round(tweet.bbox_width * scale);
          let box_height = Math.round(tweet.bbox_height * scale);
  
          let newImageHeight = Math.round(
            (tweet.imgHeight / tweet.imgWidth) * 500
          );
  
          // console.log('img W:' +  tweet.imgWidth + ' H:' + tweet.imgHeight)
          // console.log('img adjusted W: 500 H:' + newImageHeight)
          // console.log('box L:' +  tweet.bbox_left + ' P:' + tweet.bbox_top + ' W:' +  tweet.bbox_width + ' H:' + tweet.bbox_height )
          // console.log('box adjusted L:' +  box_left + ' P:' + box_top + ' W:' +  box_width + ' H:' + box_height )
  
          // var canvas = document.createElement("canvas");
          // canvas.setAttribute("id", id);
          var canvas = document.getElementById(id);
          var context = canvas.getContext("2d");
  
          var img = new Image();
          img.onload = function() {
            canvas.width = 500;
            canvas.height = (tweet.imgHeight / tweet.imgWidth) * 500;
            context.drawImage(
              img,
              0,
              0,
              tweet.imgWidth,
              tweet.imgHeight,
              0,
              0,
              500,
              newImageHeight
            );
            context.lineWidth = 3;
            context.beginPath();
            context.rect(
              Math.round(box_left),
              Math.round(box_top),
              Math.round(box_width),
              Math.round(box_height)
            );
            context.strokeStyle = "green";
            context.stroke();
          };
          img.src = tweet.image_url;
        } catch (e) {
          console.error(e);
        }
      },
      delImage(tweet) {
        //console.log("del: " + id + " - " + emotion + " - " + this.baseUrl);
        try {
          //console.log("calling " + this.baseUrl);
          axios.post(this.baseUrl + "/delimage", {
              tweet: tweet
            })
            .then(function(response) {
              console.log(response);
              var photo = document.getElementById('canvas_' + tweet.etype);
              photo.remove(); 
            })
            .catch(function(error) {
              console.error(error);
            });
        } catch (error) {
          console.error(error);
        }
      }
    }
  };
  </script>