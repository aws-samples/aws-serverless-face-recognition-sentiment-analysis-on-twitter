<template>
  <div class="flex flex-wrap justify-content-around gap-3">
    <Card>
      <template #title>
        Twitter Face detection/sentiment analisys app
          </template>
          <template #subtitle>
            <span>This demo uses the AWS Reckognition's moderation feature, but from occasionally inappropriate photos can appear.
            Please use the delete icon to remove these photos from the database.</span>            
          </template>
          <template #content>
            <div class="grid">
        <div class="col-3">
          <Chart type="bar" :data="yearChartData" :options="barChartOptions" />
        </div>
        <div class="col-3">
          <Chart type="bar" :data="weekChartData" :options="barChartOptions" />
        </div>
        <div class="col-6">
          <Chart type="line" :data="hourChartData" :options="lineChartOptions" />
        </div>
      </div>
          </template>
    </Card>

    <div class="grid">
      <div v-for="emotion in emotions" :key="emotion" class="col-6">
        <ImageCard :emotion="emotion"> </ImageCard>
      </div>
    </div>
  </div>
</template>

<script>
import ImageCard from "./components/ImageCard.vue"
import moment from "moment";
import axios from "axios";

export default {
  name: "home",
  components: {
    ImageCard
  },
  data() {
    return {
      baseUrl: import.meta.env.VITE_API_URL,
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
      hourChartData: null,
      weekChartData: null,
      yearChartData: null,
      lineChartOptions: null,
      barChartOptions: null,
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
      await axios.get(this.baseUrl + "stat").then((results) => {
        this.hourChartData = this.setDayChartData(results.data.days);
        this.weekChartData = this.setMonthChartData(results.data.month);
        this.yearChartData = this.setYearChartData(results.data.year);
        //console.log(results.data)
      });
    } catch (error) {
      console.error(error);
    }
    this.lineChartOptions = this.setLineChartOptions();
    this.barChartOptions = this.setBarChartOptions();
  },
  methods: {
    setYearChartData(data) {
      const documentStyle = getComputedStyle(document.documentElement);

      var labels = [];
      var tp_values = [];

      for (let k in data.Chart1TweetsProcessed) {
        labels.push(k)
        tp_values.push(parseFloat(data.Chart1TweetsProcessed[k]))
      }

      return {
        labels: labels,
        datasets: [
          {
            label: 'Tweets Processed',
            backgroundColor: documentStyle.getPropertyValue('--blue-500'),
            borderColor: documentStyle.getPropertyValue('--blue-500'),
            data: tp_values
          }
        ]
      };
    },
    setMonthChartData(data) {
      const documentStyle = getComputedStyle(document.documentElement);

      var labels = [];
      var tp_values = [];
      var ii_values = [];
      var im_values = [];
      var fp_values = [];

      for (let k in data.Chart1TweetsProcessed) {
        labels.push(k)
        tp_values.push(parseFloat(data.Chart1TweetsProcessed[k]))
        ii_values.push(parseFloat(data.Chart1ImagesIdentified[k]))
        im_values.push(parseFloat(data.Chart1ImagesModerated[k]))
        fp_values.push(parseFloat(data.Chart1FacesProcessed[k]))
      }

      return {
        labels: labels,
        datasets: [
          {
            label: 'Tweets Processed',
            backgroundColor: documentStyle.getPropertyValue('--blue-500'),
            borderColor: documentStyle.getPropertyValue('--blue-500'),
            data: tp_values
          },
          {
            label: 'Images Identified',
            backgroundColor: documentStyle.getPropertyValue('--green-500'),
            borderColor: documentStyle.getPropertyValue('--green-500'),
            data: ii_values
          },
          {
            label: 'Images Moderated',
            backgroundColor: documentStyle.getPropertyValue('--pink-500'),
            borderColor: documentStyle.getPropertyValue('--pink-500'),
            data: ii_values
          },
          {
            label: 'Faces Processed',
            backgroundColor: documentStyle.getPropertyValue('--orange-500'),
            borderColor: documentStyle.getPropertyValue('--orange-500'),
            data: ii_values
          }
        ]
      };
    },
    setDayChartData(data) {
      const documentStyle = getComputedStyle(document.documentElement);

      var labels = [];
      var tp_values = [];
      var ii_values = [];
      var im_values = [];
      var fp_values = [];

      for (let k in data.Chart1TweetsProcessed) {
        labels.push(k)
        tp_values.push(parseFloat(data.Chart1TweetsProcessed[k]))
        ii_values.push(parseFloat(data.Chart1ImagesIdentified[k]))
        im_values.push(parseFloat(data.Chart1ImagesModerated[k]))
        fp_values.push(parseFloat(data.Chart1FacesProcessed[k]))
      }
      return {
        labels: labels,
        datasets: [
          {
            label: 'Tweets Processed',
            data: tp_values,
            fill: false,
            borderColor: documentStyle.getPropertyValue('--blue-500'),
            tension: 0.4
          },
          {
            label: 'Images Identified',
            data: ii_values,
            fill: false,
            borderColor: documentStyle.getPropertyValue('--green-500'),
            tension: 0.4
          },
          {
            label: 'Images Moderated',
            data: im_values,
            fill: false,
            borderColor: documentStyle.getPropertyValue('--pink-500'),
            tension: 0.4
          },
          {
            label: 'Faces Processed',
            data: fp_values,
            fill: false,
            borderColor: documentStyle.getPropertyValue('--orange-500'),
            tension: 0.4
          }
        ]
      };
    },
    setLineChartOptions() {
      const documentStyle = getComputedStyle(document.documentElement);
      const textColor = documentStyle.getPropertyValue('--text-color');
      const textColorSecondary = documentStyle.getPropertyValue('--text-color-secondary');
      const surfaceBorder = documentStyle.getPropertyValue('--surface-border');

      return {
        maintainAspectRatio: false,
        aspectRatio: 0.6,
        plugins: {
          legend: {
            labels: {
              color: textColor,
              boxWidth: 20
            },
            position: 'bottom'            
          }
        },
        scales: {
          x: {
            ticks: {
              color: textColorSecondary
            },
            grid: {
              color: surfaceBorder
            }
          },
          y: {
            ticks: {
              color: textColorSecondary
            },
            grid: {
              color: surfaceBorder
            }
          }
        }
      };
    },
    setBarChartOptions() {
      const documentStyle = getComputedStyle(document.documentElement);
      const textColor = documentStyle.getPropertyValue('--text-color');
      const textColorSecondary = documentStyle.getPropertyValue('--text-color-secondary');
      const surfaceBorder = documentStyle.getPropertyValue('--surface-border');

      return {
        maintainAspectRatio: false,
        aspectRatio: 0.6,
        plugins: {
          legend: {
            labels: {
              fontColor: textColor,
              boxWidth: 20
            },
            position: 'bottom'
          }
        },
        scales: {
          x: {
            ticks: {
              color: textColorSecondary,
              font: {
                weight: 500
              }
            },
            grid: {
              display: false,
              drawBorder: false
            }
          },
          y: {
            ticks: {
              color: textColorSecondary
            },
            grid: {
              color: surfaceBorder,
              drawBorder: false
            }
          }
        }
      };
    }
  }
};


</script>
