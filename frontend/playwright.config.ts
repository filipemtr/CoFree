import {defineConfig,devices} from '@playwright/test';
export default defineConfig({testDir:'./e2e',timeout:90000,expect:{timeout:15000},fullyParallel:false,retries:1,
 reporter:[['list'],['html',{open:'never'}]],use:{baseURL:process.env.BASE_URL||'http://localhost:3000',trace:'retain-on-failure',screenshot:'only-on-failure'},
 projects:[{name:'chromium',use:{...devices['Desktop Chrome']}},{name:'mobile',use:{...devices['iPhone 13'],browserName:'chromium'}}]});
