<template>
  <q-layout view="hHh lpR fFf">
    <q-header bordered class="bg-primary text-white" height-hint="98">
      <q-toolbar>
        <q-btn flat round dense icon="house" class="q-mr-sm" />
        <q-separator dark vertical inset />
        <!-- <q-btn color="primary" icon-right="refresh" label="Refresh page" @click="refreshPage"/> -->
        <q-toolbar-title>Twitter Face detection/sentiment analisys Demo</q-toolbar-title> <span caption>Rank from the last 48 hours</span>
      </q-toolbar>
      <q-banner class="bg-red text-white">
        <span class="text-weight-bolder">Twitter is a public platform that does not moderate photos</span> uploaded by its users. This demo uses the AWS Reckognition's moderation feature, but from occasionally inappropriate photos can appear. Please use the delete icon to remove these photos from the database.    
    </q-banner>
    </q-header>

    <q-page-container>
      <router-view />      
    </q-page-container>
  </q-layout>
</template>

<script>
export default {
  data() {
    return {
        baseUrl: process.env.VUE_APP_AWS_API_URL
    };
  },
};
</script>


