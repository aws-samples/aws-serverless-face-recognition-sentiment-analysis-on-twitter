import { createApp } from 'vue'
import App from './App.vue'

import PrimeVue from 'primevue/config';

import Button from 'primevue/button';
import InputText from 'primevue/inputtext';
import ProgressBar from 'primevue/progressbar';
import Toolbar from 'primevue/toolbar';
import Message from 'primevue/message';
import Card from 'primevue/card';
import Chart from 'primevue/chart';

import 'primevue/resources/primevue.min.css';
import 'primevue/resources/themes/soho-dark/theme.css';
import 'primeicons/primeicons.css';
import 'primeflex/primeflex.css';

const app = createApp(App)

app.use(PrimeVue);
app.component('Button', Button);
app.component('InputText', InputText);
app.component('ProgressBar', ProgressBar);
app.component('Toolbar', Toolbar);
app.component('Message', Message);
app.component('Card', Card);
app.component('Chart', Chart);

app.mount('#app')
