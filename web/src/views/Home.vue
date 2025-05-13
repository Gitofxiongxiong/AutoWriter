<template>
  <div class="home">
    <div class="table-recognition-section">
      <h2>文档识别</h2>
      <div class="recognition-container">
        <div class="image-preview">
          <div class="preview-header">
            <span class="title">效果测试</span>
            <div class="controls">
              <el-button link size="small">上一张</el-button>
              <span class="page-info">1 / 1</span>
              <el-button link size="small">下一张</el-button>
            </div>
          </div>
          
          <div class="preview-content" v-if="previewImage">
              <el-image 
                ref="previewImg"
                :src="previewImage" 
                alt="预览图片" 
                class="preview-img"
                v-loading="loading"
                element-loading-text="正在识别中..."
              />   

              <!-- <canvas ref="tableCanvas" class="table-canvas"></canvas> -->

          </div>
          
          <div class="preview-placeholder" v-else>
            <el-upload
              class="upload-demo"
              drag
              action="#"
              :auto-upload="false"
              :show-file-list="false"
              :on-change="handleFileChange">
              <i class="el-icon-upload"></i>
              <div class="el-upload__text">
                拖拽图片到此处，或<em>点击上传</em>
              </div>
              <template #tip>
                <div class="el-upload__tip">
                  支持格式：.png / .jpg / .jpeg / .bmp 等<br>
                  图片大小不超过10M，最长边不超过8192像素
                </div>
              </template>
            </el-upload>
          </div>
        </div>
        
        <div class="recognition-result">
          <div class="result-header">
            <span class="title">识别结果</span>
            <div class="header-buttons">
              <el-button size="small" type="primary" @click="saveTableData">编辑完成</el-button>
              <el-button size="small" type="danger" @click="clearTableData">清空</el-button>
            </div>
          </div>
          
          <div class="result-content">
            <div v-if="detectResult.web_tdtr_data !== null" class="web-tdtr-table-container">
              <h3>表格识别结果</h3>
              <table class="editable-table">
                <tr v-for="(row, rowIndex) in detectResult.web_tdtr_data.tdtr_cells" :key="rowIndex">
                  <td v-for="(cell, colIndex) in getVisibleCells(row)" 
                    :key="colIndex"
                    :rowspan="cell.rowSpan"
                    :colspan="cell.colSpan"
                    :style="{ textAlign: cell.textAlign, minWidth: '50px' }"
                    >
                       <!-- 情况1：不可编辑单元格，只显示原始文本 -->
                        <span v-if="!cell.isEditable && cell.originalText"
                              :style="{
                                display: 'inline-block',
                                fontFamily: 'Arial',
                                fontSize: '8px',
                                color: 'gray',
                                fontWeight: 'bold',
                                cursor: 'default',
                                display: 'inline-block',
                                width: '100%',  
                                textAlign: cell.originalAlign
                              }">       
                          {{ cell.originalText }}
                      </span>
            
                      <!-- 情况2：可编辑单元格，但没有原始文本，显示用户输入的文本 -->
                      <span v-else-if="cell.isEditable && !cell.originalText"
                            :style="{
                              display: 'inline-block',
                              fontFamily: 'Arial',
                              fontSize: '8px',
                              color: 'black',
                              fontWeight: 'bold',
                              cursor: 'pointer',
                              border: '1px dashed blue',
                              width: '100%',
                              height: '100%',
                              minHeight: '8px',
                              textAlign: 'left',
                              whiteSpace: 'pre-wrap' // 允许换行
                            }"
                            @click="showEditDialog(cell)">
                        {{ cell.text }}
                      </span>
            
                       <!-- 情况3：可编辑单元格，有原始文本，同时显示原始文本和用户输入的文本 -->
                      <span v-else-if="cell.isEditable && cell.originalText"
                            :style="{
                              display: 'inline-block',
                              fontFamily: 'Arial',
                              fontSize: '8px',
                              fontWeight: 'bold',
                              cursor: 'pointer',
                              border: '1px dashed blue',
                              width: '100%',
                              height: '100%'
                            }"
                            @click="showEditDialog(cell)">
                        <div :style="{ color: 'gray', textAlign: cell.originalAlign }">{{ cell.originalText }}</div>
                        <div :style="{ color: 'black', textAlign: 'left' ,whiteSpace: 'pre-wrap' }">{{ cell.text }}</div>
                      </span>
            
                        <!-- 情况4：其他情况，如空单元格 -->
                      <span v-else
                              :style="{
                                display: 'inline-block',
                                textAlign: 'left',
                                outline: 'none',
                                fontSize: '8px',
                                width: '100%',
                                height: '100%',
                                whiteSpace: 'pre-wrap',
                                wordWrap: 'break-word',
                                boxSizing: 'border-box',
                                cursor: cell.isEditable ? 'pointer' : 'default',
                                marginLeft: '-4px',
                                border: '1px dashed black', // 黑色虚线边框
                              }"
                              @click="cell.isEditable && showEditDialog(cell)">

                              <span :style="{
                                              display: 'inline-block',
                                              width: '100%',
                                              height: '100%',
                                            }">
                              </span>
                       </span>           

                  </td>
                </tr>
              </table>
            </div>
            
            <div v-else class="no-result">
              <p>请上传图片并选择识别区域查看结果</p>
            </div>
          </div>
        </div>
      </div>
    </div>
    
  </div>
</template>

<script>
// 导入新创建的 API 函数
import { detectTableImage, genHwImage } from '@/api/img_proc';
export default {
  name: 'HomePage',
  data() {
    return {
      previewImage: null,
      selectedRegion: null,
      resultFormat: 'structured',
      loading: false,
      detectResult:{web_tdtr_data:null,corrected_table_info:null},
      img_index_key: ""
    };
  },
  methods: {
    getVisibleCells(row){94

      console.log(row)
      return row.filter(cell => cell.isValid == true);
    },

    handleCellClick(cell){
      alert('点击了单元格：' + cell.tableCellId + "--" + cell.originalText);
    },


    showEditDialog(cell) {
      // 创建弹框内容
      const dialogContent = `
        <div class="edit-dialog">
          <div class="dialog-title" style="
            font-size: 16px;
            font-weight: bold;
            margin-bottom: 15px;
            color: #303133;
            border-bottom: 1px solid #e4e7ed;
            padding-bottom: 10px;
          ">单元格 ${cell.tableCellId}</div>
          ${cell.originalText ? 
            `<div class="original-text" style="
              color: #409eff;
              margin-bottom: 10px;
              padding: 8px;
              background: #f5f5f5;
              border-radius: 4px;
              font-size: 14px;
              font-weight: bold;
            ">${cell.originalText}</div>` : ''
          }
          <textarea class="edit-textarea">${cell.text || ''}</textarea>
          <select class="align-select">
            <option value="center" ${cell.align === 'center' ? 'selected' : ''}>居中对齐</option>
            <option value="left bottom" ${cell.align === 'left bottom' ? 'selected' : ''}>左下对齐</option>
            <option value="center bottom" ${cell.align === 'center bottom' ? 'selected' : ''}>中下对齐</option>
            <option value="left middle" ${cell.align === 'left middle' ? 'selected' : ''}>左中对齐</option>
            <option value="left top" ${cell.align === 'left top' ? 'selected' : ''}>左上对齐</option>
            <option value="center top" ${cell.align === 'center top' ? 'selected' : ''}>中上对齐</option>
          </select>
          <div class="button-group">
            <button class="confirm-btn">确认</button>
            <button class="cancel-btn">退出</button>
          </div>
        </div>
      `;
      
      // 显示弹框
      const dialog = document.createElement('div');
      dialog.className = 'edit-dialog-container';
      dialog.innerHTML = dialogContent;
      document.body.appendChild(dialog);
      
      // 添加样式
      dialog.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-color: rgba(0, 0, 0, 0.5);
        display: flex;
        justify-content: center;
        align-items: center;
        z-index: 9999;
      `;
      
      const editDialog = dialog.querySelector('.edit-dialog');
      editDialog.style.cssText = `
        background-color: white;
        padding: 20px;
        border-radius: 8px;
        width: 400px;
        max-width: 90%;
        box-shadow: 0 2px 12px rgba(0, 0, 0, 0.15);
      `;
      
      const textarea = dialog.querySelector('.edit-textarea');
      textarea.style.cssText = `
        width: 100%;
        min-height: 100px;
        margin: 10px 0;
        padding: 8px;
        border: 1px solid #dcdfe6;
        border-radius: 4px;
        resize: vertical;
        font-size: 14px;
      `;
      
      const select = dialog.querySelector('.align-select');
      select.style.cssText = `
        width: 100%;
        margin: 10px 0;
        padding: 8px;
        border: 1px solid #dcdfe6;
        border-radius: 4px;
        font-size: 14px;
      `;
      
      const buttonGroup = dialog.querySelector('.button-group');
      buttonGroup.style.cssText = `
        display: flex;
        justify-content: flex-end;
        margin-top: 15px;
      `;
      
      const buttons = dialog.querySelectorAll('button');
      buttons.forEach(button => {
        button.style.cssText = `
          padding: 8px 15px;
          margin-left: 10px;
          border-radius: 4px;
          font-size: 14px;
          cursor: pointer;
          border: none;
        `;
      });
      
      const confirmBtn = dialog.querySelector('.confirm-btn');
      confirmBtn.style.cssText += `
        background-color: #409EFF;
        color: white;
      `;
      
      const cancelBtn = dialog.querySelector('.cancel-btn');
      cancelBtn.style.cssText += `
        background-color: #f5f7fa;
        color: #606266;
        border: 1px solid #dcdfe6;
      `;
      
      // 确认按钮点击事件
      dialog.querySelector('.confirm-btn').addEventListener('click', () => {
        const text = dialog.querySelector('.edit-textarea').value;
        const align = dialog.querySelector('.align-select').value;
        
        // 更新单元格数据
        if (cell.tableCellId) {
          // 在表格数据中找到对应的单元格并更新
          const rows = this.detectResult.web_tdtr_data.tdtr_cells;
          for (let i = 0; i < rows.length; i++) {
            for (let j = 0; j < rows[i].length; j++) {
              if (rows[i][j].tableCellId === cell.tableCellId) {
                rows[i][j].text = text;
                rows[i][j].textAlign = align;
                break;
              }
            }
          }
        }
        
        // 关闭弹框
        document.body.removeChild(dialog);
      });
      
      // 退出按钮点击事件
      dialog.querySelector('.cancel-btn').addEventListener('click', () => {
        document.body.removeChild(dialog);
      });
      
      // 点击背景关闭弹框
      dialog.addEventListener('click', (e) => {
        if (e.target === dialog) {
          document.body.removeChild(dialog);
        }
      });
      
      // 聚焦文本框
      textarea.focus();
    },

    clearTableData() {
      // 确保表格数据存在
      if (this.detectResult && this.detectResult.web_tdtr_data && this.detectResult.web_tdtr_data.tdtr_cells) {
        // 遍历所有单元格
        const rows = this.detectResult.web_tdtr_data.tdtr_cells;
        for (let i = 0; i < rows.length; i++) {
          for (let j = 0; j < rows[i].length; j++) {
            // 清空文本内容
            rows[i][j].text = '';
            // 将文本对齐方式设置为居中
            rows[i][j].textAlign = 'center';
          }
        }
        this.$message.success('表格数据已清空');
      } else {
        this.$message.warning('没有表格数据可清空');
      }
    },
    
    async saveTableData() {
      try {
        if (!this.detectResult.web_tdtr_data || !this.img_index_key) {
          this.$message.error('没有可用的表格数据或图片索引');
          return;
        }
        
        this.loading = true;
        
        // 准备请求数据
        const requestData = {
          ...this.detectResult.web_tdtr_data,
          img_index_key: this.img_index_key
        };
        
        // 调用生成手写字图片接口
        const result = await genHwImage(requestData);
        
        if (result.success && result.handwriting_image_id) {
          // 显示生成的手写字图片
          const imgBaseUrl = process.env.VUE_APP_BASE_API + '/img_proc/image/';
          this.previewImage = imgBaseUrl + result.handwriting_image_id;
          this.$message.success('手写字图片生成成功');
        } else {
          this.$message.error('生成手写字图片失败');
        }
      } catch (error) {
        console.error('生成手写字图片时发生错误:', error);
        this.$message.error(`生成失败: ${error.message || '未知错误'}`);
      } finally {
        this.loading = false;
      }
    },

    async handleFileChange(file) {
      if (!file) return;
      
      // 文件类型检查
      const allowedTypes = ['image/jpeg', 'image/png', 'image/bmp'];
      if (!allowedTypes.includes(file.raw.type)) {
        this.$message.error('只支持 JPG、PNG 和 BMP 格式的图片！');
        return;
      }

      // 文件大小检查（10MB）
      const maxSize = 10 * 1024 * 1024;
      if (file.raw.size > maxSize) {
        this.$message.error('图片大小不能超过 10MB！');
        return;
      }

      try {

        // 准备发送到服务器
        const formData = new FormData();
        formData.append('file', file.raw);

        this.loading = true;
        const result = await detectTableImage(formData); // result 已经是响应拦截器处理过的 data 部分 (如果拦截器这样配置的话)
        const imgBaseUrl = process.env.VUE_APP_BASE_API+'/img_proc/image/';
        // 显示带表格的的图片（如果有）
        if (result.success && result.drawed_image_id && result.img_index_key) {
          // 更新预览图片为带表格的的图片
          this.img_index_key = result.img_index_key;
          this.previewImage = imgBaseUrl+result.drawed_image_id;
        } else if (result.success && result.original_image_id && result.img_index_key) {
          // 如果没有校正后的图片，但有原始图片ID，则显示原始图片
          this.img_index_key = result.img_index_key;
          this.previewImage = imgBaseUrl+result.original_image_id;
        } else {
          // 如果没有任何图片ID，则显示本地预览
          this.previewImage = URL.createObjectURL(file.raw);
        }
        if (result.success) {
          // 存储表格数据
          if (result.web_tdtr_data) {
            this.detectResult.web_tdtr_data = result.web_tdtr_data;
          }
          
          // 存储校正后的表格信息
          if (result.corrected_table_info) {
            this.detectResult.corrected_table_info = result.corrected_table_info;
          }
        }
        console.log(this.detectResult);
        
        this.$message.success('识别成功！');

      } catch (error) {
        console.error('上传或识别失败:', error);
        // request.js 中的拦截器已经处理了错误提示，这里可以根据需要添加额外的逻辑
        // this.$message.error(error.message || '上传或识别失败，请重试！');
      } finally {
        this.loading = false;
      }
    },

    
    // 计算坐标变换
    calculateCoordinateTransform(imgEl) {
    // 获取图片的原始尺寸
    const naturalWidth = imgEl.naturalWidth;
    const naturalHeight = imgEl.naturalHeight;
    
    // 获取图片的显示尺寸
    const displayWidth = imgEl.clientWidth;
    const displayHeight = imgEl.clientHeight;
    
    // 计算缩放比例
    const scaleX = displayWidth / naturalWidth;
    const scaleY = displayHeight / naturalHeight;
    const imgRect = imgEl.getBoundingClientRect();
    
    const offsetX = imgRect.left;
    const offsetY = imgRect.top;
    console.log('图片相对位置偏移:', offsetX, offsetY);

    // 打印scaleX和scaleY，用于调试
    console.log('scaleX:', scaleX);
    console.log('scaleY:', scaleY);
    // 返回坐标转换函数
    return {
      scaleX,
      scaleY,
    };
    },
    
  //   drawTable() {
  //   // 获取canvas元素和图片元素
  //   const canvas = this.$refs.tableCanvas;
  //   const img = this.$refs.previewImg;
  //   const table_info = this.detectResult.corrected_table_info.data;
  //   if (!canvas || !img || !img.$el || !table_info) {
  //     console.log('缺少必要元素或数据，无法绘制表格');
  //     return;
  //   }
    
  //   // 获取图片的实际显示尺寸和位置
  //   const imgEl = img.$el.querySelector('img');
    
  //   if (!imgEl) {
  //     console.log('无法获取图片元素');
  //     return;
  //   } 
    
  //   // 如果图片尚未加载完成，等待加载
  //   if (imgEl.naturalWidth === 0 || imgEl.naturalHeight === 0) {
  //     console.log('图片尚未加载完成，等待加载...');
  //     imgEl.onload = () => {
  //       console.log('图片加载完成，开始绘制表格');
  //       this.drawTable(); // 图片加载完成后重新调用
  //     };
  //     return;
  //   }

  //   // 计算坐标变换
  //  const transform = this.calculateCoordinateTransform(imgEl);
  //   // 设置canvas尺寸与图片显示尺寸一致
  //   canvas.width = imgEl.clientWidth;
  //   canvas.height = imgEl.clientHeight;
  //   console.log('canvas尺寸:', canvas.width, canvas.height);
    
    
  //   const ctx = canvas.getContext('2d');
  //   ctx.clearRect(0, 0, canvas.width, canvas.height);

  //   // 确保表格数据存在
  //   if (!table_info.prism_tablesInfo || 
  //       !table_info.prism_tablesInfo[0] ||
  //       !table_info.prism_tablesInfo[0].cellInfos) {
  //     console.log('表格数据结构不完整');
  //     return;
  //   }
    
  //   // 绘制单元格边框
  //   const cellInfos = table_info.prism_tablesInfo[0].cellInfos;
    
  //   cellInfos.forEach(cell => {
  //     ctx.beginPath();
  //     cell.pos.forEach((p, i) => {
  //       // 应用坐标变换
  //       const x =  Math.round(p.x * transform.scaleX);
  //       const y =  Math.round(p.y * transform.scaleY);
  //       ctx[i === 0 ? 'moveTo' : 'lineTo'](x, y);

  //     });
  //     ctx.closePath();
  //     ctx.strokeStyle = '#ff0000';
  //     ctx.lineWidth = 2;
  //     ctx.stroke();
  //   });
    
  //   // 如果有文字信息，绘制文字
  //   if (table_info.prism_wordsInfo) {
  //     table_info.prism_wordsInfo.forEach(wordInfo => {
  //       if (wordInfo.word && wordInfo.pos && Array.isArray(wordInfo.pos) && wordInfo.pos.length >= 4) {
  //         // 设置文字样式
  //         const fontSize = Math.round(Math.max(5, (wordInfo.width || 8) * transform.scaleX));
  //         console.log('字体大小:', fontSize);
  //         ctx.font = `${fontSize}px Arial`;
  //         ctx.fillStyle = '#0000ff';
  //         ctx.textAlign = 'center';
  //         ctx.textBaseline = 'middle';
          
  //         // 计算文字中心点（四个角的平均值）并应用坐标变换
  //         const centerX = Math.round(((wordInfo.pos[0].x + wordInfo.pos[1].x + wordInfo.pos[2].x + wordInfo.pos[3].x) / 4) * transform.scaleX);
  //         const centerY = Math.round(((wordInfo.pos[0].y + wordInfo.pos[1].y + wordInfo.pos[2].y + wordInfo.pos[3].y) / 4) * transform.scaleY);
          
  //         // 绘制文字
  //         ctx.fillText(wordInfo.word, centerX, centerY);
  //       }
  //     });
  //   }
    
  //   console.log('表格绘制完成');
  //   },
    
    selectRegion(index) {
      this.selectedRegion = index;
    }
  }
};
</script>

<style scoped>
.home {
  text-align: center;
  padding: 20px;
}

.banner {
  margin-bottom: 40px;
}

h1 {
  margin-top: 20px;
  color: #333;
}

p {
  color: #666;
  font-size: 18px;
}

.section-desc {
  max-width: 600px;
  margin: 0 auto 30px;
  color: #666;
}

.features {
  margin-top: 40px;
  max-width: 1200px;
  margin-left: auto;
  margin-right: auto;
  margin-bottom: 60px;
}

.el-card {
  margin-bottom: 20px;
  height: 150px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.table-recognition-section {
  max-width: 1200px;
  margin: 20px auto;
  text-align: left;
}

.table-recognition-section h2 {
  text-align: center;
  margin-bottom: 20px;
  color: #333;
}

.recognition-container {
  display: flex;
  border: 1px solid #e6e6e6;
  border-radius: 4px;
  overflow: hidden;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.image-preview {
  flex: 1;
  border-right: 1px solid #e6e6e6;
  min-height: 500px;
  position: relative;
}

.preview-header, .result-header {
  padding: 12px 15px;
  border-bottom: 1px solid #e6e6e6;
  background-color: #f5f7fa;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.title {
  font-weight: bold;
  color: #333;
}

.controls {
  display: flex;
  align-items: center;
}

.page-info {
  margin: 0 10px;
  color: #666;
}

.preview-content {
  background-color: #e6e6e6;
  position: relative;
  max-width: 400px;
  max-height: 800px;
  margin: 10px auto;
}

.edit-dialog-container {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-buttons {
  display: flex;
  gap: 10px;
}
.table-canvas {
  display: block;
  position: absolute;
  left: 50%;
  transform: translate(-50%, 0); /* 使用transform实现精确居中 */
  max-width: 100%;
  max-height: 100%;
  pointer-events: none; /* 允许点击穿透到下方的图片 */
}

.region {
  position: absolute;
  border: 2px solid #409EFF;
  background-color: rgba(64, 158, 255, 0.1);
  cursor: pointer;
}

.region-label {
  position: absolute;
  top: -25px;
  left: 0;
  background-color: #409EFF;
  color: white;
  padding: 2px 8px;
  font-size: 12px;
  border-radius: 2px;
}

.preview-placeholder {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
  min-height: 300px;
  background-color: #f5f7fa;
}

.recognition-result {
  flex: 1;
  min-height: 500px;
  display: flex;
  flex-direction: column;
}

.result-content {
  flex: 1;
  overflow-y: auto;
  padding: 15px;
}

.region-info {
  border: 1px solid #e6e6e6;
  border-radius: 4px;
}

.region-header {
  padding: 10px 15px;
  background-color: #f5f7fa;
  border-bottom: 1px solid #e6e6e6;
  font-weight: bold;
}

.region-details {
  padding: 15px;
}

.detail-item {
  display: flex;
  margin-bottom: 10px;
  font-size: 14px;
}

.item-label {
  width: 120px;
  color: #666;
}

.item-value {
  flex: 1;
  color: #333;
}

.json-result {
  padding: 15px;
  background-color: #f5f7fa;
  border-radius: 4px;
  font-family: monospace;
  font-size: 14px;
  white-space: pre-wrap;
  overflow-x: auto;
}

.no-result {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
  color: #909399;
}

.editable-table {
  border-collapse: collapse;
  width: 100%;
}

.editable-table td {
  border: 1px solid gray;  /* 修改为灰色边框 */
  padding: 8px;
  min-height: 30px;  /* 设置最小高度 */
  height: auto;      /* 高度自动适应内容 */
}

</style>