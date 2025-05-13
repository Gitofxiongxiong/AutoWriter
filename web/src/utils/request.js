import axios from 'axios'
import { ElMessage } from 'element-plus'

// 创建axios实例
const service = axios.create({
  baseURL: process.env.VUE_APP_BASE_API || '', // url = base url + request url
  timeout: 30000 // 请求超时时间
})

// 请求拦截器
service.interceptors.request.use(
  config => {
    // 可以在这里设置请求头等信息
    return config
  },
  error => {
    console.log(error)
    return Promise.reject(error)
  }
)

// 响应拦截器
service.interceptors.response.use(
  response => {

    return response.data

    // const res = response.data
    // // 如果返回的状态码不是0，则判断为错误
    // if (res.code !== 0) {
    //   ElMessage({
    //     message: res.message || '请求失败',
    //     type: 'error',
    //     duration: 5 * 1000
    //   })
      
    //   return Promise.reject(new Error(res.message || '请求失败'))
    // } else {
    //   return res
    // }
  },
  error => {
    console.log('请求错误', error)
    ElMessage({
      message: error.message || '请求失败',
      type: 'error',
      duration: 5 * 1000
    })
    return Promise.reject(error)
  }
)

export default service