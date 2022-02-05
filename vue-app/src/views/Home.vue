<template>
  <div class="q-pa-md q-gutter-md">
    <div class="row">
      <div class="row q-pa-md q-gutter-md">
        <q-card class="stats">
          <q-card-section>
            <div class="text-h6">App statistics</div>
          </q-card-section>
          <q-markup-table>
            <thead>
              <tr>
                <th class="text-left"></th>
                <th class="text-right">Last 24 hours</th>
                <th class="text-right">Last 7 days</th>
                <th class="text-right">Last 30 days</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td class="text-left text-bold">Tweets received</td>
                <td class="text-right">{{ tweetsProcessed["1"] }}</td>
                <td class="text-right">{{ tweetsProcessed["7"] }}</td>
                <td class="text-right">{{ tweetsProcessed["30"] }}</td>
              </tr>
              <tr>
                <td class="text-left text-bold">Images processed</td>
                <td class="text-right">{{ imagesIdentified["1"] }}</td>
                <td class="text-right">{{ imagesIdentified["7"] }}</td>
                <td class="text-right">{{ imagesIdentified["30"] }}</td>
              </tr>
              <tr>
                <td class="text-left text-bold">Images moderated</td>
                <td class="text-right">{{ imagesModerated["1"] }}</td>
                <td class="text-right">{{ imagesModerated["7"] }}</td>
                <td class="text-right">{{ imagesModerated["30"] }}</td>
              </tr>
              <tr>
                <td class="text-left text-bold">Faces identified</td>
                <td class="text-right">{{ facesProcessed["1"] }}</td>
                <td class="text-right">{{ facesProcessed["7"] }}</td>
                <td class="text-right">{{ facesProcessed["30"] }}</td>
              </tr>
            </tbody>
          </q-markup-table>
        </q-card>
      </div>
     <div class="row q-pa-md q-gutter-md">
        <q-card>
          <img v-bind:src="'data:image/png;base64,' + metricWidgetImage" />
        </q-card>
      </div>
    </div>
    <div class="row q-pa-md q-gutter-md">
      <div v-for="emotion in emotions" :key="emotion">
        <ImageCard :emotion="emotion"> </ImageCard>
      </div>
    </div>
  </div>
</template>

<script>
import ImageCard from "../components/ImageCard";

export default {
  name: "home",
  components: {
    ImageCard,
  },
  data() {
    return {
      baseUrl: process.env.VUE_APP_AWS_API_URL,
      emotions: [
        "HAPPY",
        "SAD",
        "ANGRY",
        "CONFUSED",
        "DISGUSTED",
        "SURPRISED",
        "CALM",
        "FEAR",
      ],
      emotion: null,
      tweetsProcessed: {},
      imagesIdentified: {},
      facesProcessed: {},
      imagesModerated: {},
      metricWidgetImage: null,
    };
  },
  async mounted() {
    try {
      await this.$http.get(this.baseUrl + "stat").then((results) => {
        this.tweetsProcessed = results.data.TweetsProcessed;
        this.imagesIdentified = results.data.ImagesIdentified;
        this.facesProcessed = results.data.FacesProcessed;
        this.imagesModerated = results.data.ImagesModerated;
        this.metricWidgetImage = results.data.MetricWidgetImage;
      });
    } catch (error) {
      console.error(error);
    }
  },
};
</script>
