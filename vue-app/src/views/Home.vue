<template>
  <div>
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
                <td class="text-right">{{ tweetsProcessed["aggregation"]["one"]}}</td>
                <td class="text-right">{{ tweetsProcessed["aggregation"]["seven"]}}</td>
                <td class="text-right">{{ tweetsProcessed["aggregation"]["total"]}}</td>
              </tr>
              <tr>
                <td class="text-left text-bold">Images processed</td>
                <td class="text-right">{{ imagesIdentified["aggregation"]["one"] }}</td>
                <td class="text-right">{{ imagesIdentified["aggregation"]["seven"]}}</td>
                <td class="text-right">{{ imagesIdentified["aggregation"]["total"]}}</td>
              </tr>
              <tr>
                <td class="text-left text-bold">Images moderated</td>
                <td class="text-right">{{ imagesModerated["aggregation"]["one"]}}</td>
                <td class="text-right">{{ imagesModerated["aggregation"]["seven"]}}</td>
                <td class="text-right">{{ imagesModerated["aggregation"]["total"]}}</td>
              </tr>
              <tr>
                <td class="text-left text-bold">Faces identified</td>
                <td class="text-right">{{ facesProcessed["aggregation"]["one"]}}</td>
                <td class="text-right">{{ facesProcessed["aggregation"]["seven"]}}</td>
                <td class="text-right">{{ facesProcessed["aggregation"]["total"]}}</td>
              </tr>
            </tbody>
          </q-markup-table>
        </q-card>
        <div class="row q-pa-md q-gutter-md">
        <q-card>
           <apexchart ref="chart" height="300" :options="chartOptions" :series="t"></apexchart>
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
import VueApexCharts from "vue-apexcharts";
import moment from "moment";

export default {
  name: "home",
  components: {
    ImageCard,
    apexchart: VueApexCharts
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
      chartOptions: {
        xaxis: {
          type: 'datetime',
          tickAmount: 8,
          labels: {
              rotate: -15,
              rotateAlways: true,
              formatter: function(val, timestamp) {
                return moment(new Date(timestamp)).format("MMM Do, HH:mm")
            }
          }
        },
        title: {
          text: 'Twitter Data in Time Series',
          align: 'left',
          offsetX: 14
        },
        tooltip: {
          shared: true
        },
        chart: {
          type: 'area',
          stacked: false,
          zoom: {
            enabled: false
          },
        },
        dataLabels: {
          enabled: false
        },
        markers: {
          size: 0,
        },
        fill: {
          type: 'gradient',
          gradient: {
              shadeIntensity: 1,
              inverseColors: false,
              opacityFrom: 0.45,
              opacityTo: 0.05,
              stops: [20, 100, 100, 100]
            },
        },
      },
      tp: [{
        name: 'tweetsProcessed',
        data: []
      }],
      ii: [{
        name: 'imagesIdentified',
        data: []
      }],
      fp: [{
        name: 'facesProcessed',
        data: []
      }],
      im: [{
        name: 'imagesModerated',
        data: []
      }],
      tweetsProcessed: null,      
      imagesIdentified: null,
      facesProcessed: null,
      imagesModerated: {},
      dataSets: null,
      dataLabel: null,
    };
  },
  async mounted() {
    try {
      await this.$http.get(this.baseUrl + "stat").then((results) => {    
        this.tweetsProcessed = results.data.TweetsProcessed;        
        this.imagesIdentified = results.data.ImagesIdentified;
        this.facesProcessed = results.data.FacesProcessed;
        this.imagesModerated = results.data.ImagesModerated;
        this.dataLabel = results.data.TweetsProcessed;
      });
    } catch (error) {
      console.error(error);
    }
    this.$refs.chart.updateSeries([
      {
          name: 'tweetsProcessed',
          data: this.tweetsProcessed.data
      },
      {
        name: 'imagesIdentified',
        data: this.imagesIdentified.data
      },
      {
        name: 'facesProcessed',
        data: this.facesProcessed.data
      },
      {
        name: 'imagesModerated',
        data: this.imagesModerated.data
      },
    ])
  },
};
</script>
