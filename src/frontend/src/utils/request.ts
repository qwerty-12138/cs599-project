import axios from 'axios'

const request = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' }
})

request.interceptors.response.use(
  (res) => res.data,
  (err) => Promise.reject(err)
)

export default request
