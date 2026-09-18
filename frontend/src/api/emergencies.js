import { http } from './client.js';

const RESOURCE = '/emergencies';

export const emergencyApi = {
  list: (params) => http.get(RESOURCE, params),
  detail: (id) => http.get(`${RESOURCE}/${id}`),
  create: (payload) => http.post(RESOURCE, payload),
  update: (id, payload) => http.patch(`${RESOURCE}/${id}`, payload),
  remove: (id) => http.delete(`${RESOURCE}/${id}`),
  transitions: (id) => http.get(`${RESOURCE}/${id}/transitions`),
  handle: (id, payload) => http.post(`${RESOURCE}/${id}/handle`, payload),
  recover: (id, payload) => http.post(`${RESOURCE}/${id}/recover`, payload),
  changeStatus: (id, payload) => http.post(`${RESOURCE}/${id}/transitions`, payload),
  addRecord: (id, payload) => http.post(`${RESOURCE}/${id}/records`, payload),
};
