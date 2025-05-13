import request from '@/utils/request'

/**
 * 上传原始图片进行识别
 * @param {FormData} formData - 包含图片文件的表单数据
 * @returns {Promise} - 返回识别结果的Promise
 */
export function uploadOrgImage(formData) {
  return request({
    url: '/img_proc/uploadOrgImage',
    method: 'post',
    data: formData,
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

/**
 * 处理表格图片
 * @param {FormData} formData - 包含表格图片文件的表单数据
 * @returns {Promise} - 返回表格识别和校正结果的Promise
 */
export function detectTableImage(formData) {
  return request({
    url: '/img_proc/detect_table_image',
    method: 'post',
    data: formData,
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

/**
 * 生成手写字图片
 * @param {Object} data - 包含表格数据和图片索引键的对象
 * @returns {Promise} - 返回生成手写字图片的Promise
 */
export function genHwImage(data) {
  return request({
    url: '/img_proc/gen_hw_image',
    method: 'post',
    data
  })
}