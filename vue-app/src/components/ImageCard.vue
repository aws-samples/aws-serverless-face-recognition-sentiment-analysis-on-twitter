<template>
  <div>
    <q-card>
      <q-item v-if="loading">
        <q-linear-progress indeterminate color="orange" size="md" class="q-mt-sm" />
      </q-item>
      <q-item v-if="error">
            <q-banner inline-actions class="text-white bg-red">{{ errormsg }}.</q-banner>
      </q-item>
      <q-item>
        <q-item-section>          
          <q-item-label text-subtitle1 >{{ emotion }} - Score: {{ tweet.confidence }}</q-item-label>
          <q-item-label text-overline>Tweet Sentiment: {{ tweet.sentiment }}</q-item-label>
          <q-item-label
            caption
          >{{ tweet.first_name }} {{ tweet.last_name }} - Age {{ tweet.age }} - Gender {{ tweet.gender_value}}</q-item-label>
          <!-- <q-item-label text-body2 >Text {{ tweet.full_text }}</q-item-label> -->         
          <q-item-label caption>Updated at {{ tweet.updated_at }}</q-item-label>
        </q-item-section>
      </q-item>
      <q-card-section>
        <canvas
          :id="'canvas_' + emotion"
        />
        <q-card-actions>
          <q-btn flat color="red" icon="delete" @click="delImage(tweet)" />
        </q-card-actions>
      </q-card-section>
    </q-card>
  </div>
</template>

<script>


// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0


export default {
  data() {
    return {
        baseUrl: process.env.VUE_APP_AWS_API_URL,
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
          await this.$http.get(this.baseUrl + "image?emotion=" + this.emotion).then(results => { 
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
        this.$http
          .post(this.baseUrl + "/delimage", {
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
        this.$q.notify({
          color: "negative",
          position: "top",
          icon: "warning",
          message: "Something went wrong: " + error
        });
      }
    }
  }
};
</script>