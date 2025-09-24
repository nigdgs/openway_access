import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  thresholds: {
    http_req_duration: ['p(95)<300'],
    http_req_failed: ['rate<0.01'],
  },
  scenarios: {
    burst: {
      executor: 'ramping-arrival-rate',
      startRate: 0,
      timeUnit: '1s',
      preAllocatedVUs: 20,
      stages: [
        { duration: '10s', target: 40 },
        { duration: '20s', target: 80 },
        { duration: '10s', target: 0 },
      ],
    },
    steady: {
      executor: 'constant-arrival-rate',
      startTime: '45s',
      rate: 20,
      timeUnit: '1s',
      duration: '2m',
      preAllocatedVUs: 15,
    },
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8001';
const GATE_ID = __ENV.GATE_ID || 'gate-01';
const TOKEN = __ENV.DEVICE_TOKEN || 'dummy-token';

export default function () {
  const res = http.post(`${BASE_URL}/api/v1/access/verify`, JSON.stringify({ gate_id: GATE_ID, token: TOKEN }), {
    headers: { 'Content-Type': 'application/json' },
  });

  check(res, {
    'status is 200': (r) => r.status === 200,
    'decision present': (r) => !!r.json('decision'),
  });

  sleep(0.5);
}
