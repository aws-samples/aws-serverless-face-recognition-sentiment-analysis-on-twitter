<template>
  <div class="q-pa-md row q-gutter-md">    
    <div v-for="emotion in emotions" :key="emotion">
      <ImageCard :emotion="emotion">
      </ImageCard>
    </div>
  </div>
</template>

<script>
import ImageCard from "../components/ImageCard";

export default {
  name: "home",
  components: {
    ImageCard
  },
  data() {
    return {
      baseUrl: process.env.VUE_APP_AWS_API_URL,
      emotions: ["HAPPY","SAD","ANGRY","CONFUSED","DISGUSTED","SURPRISED","CALM","FEAR"],
      emotion: null
    };
  }
};
</script>
