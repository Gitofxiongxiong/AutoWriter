# AutoWriter Project

## 1. Project Goal

The project aims to automate the process of taking an image of a document containing a table, allow the user to verify and edit the recognized table data, and then physically reproduce the table's content in a handwritten style using a CNC machine (like a pen plotter).

The system bridges digital document processing with physical, handwritten output, effectively automating the task of transcribing table data into a handwritten format.

## 2. Project Directory Structure

The project is organized into two main parts: `backend` (a FastAPI application) and `web` (a Vue.js frontend application).

### Backend (`backend/`)

The backend handles image processing, hardware control (camera and CNC/GRBL machine), and API services.

*   **`backend/app/main.py`**: Main entry point for the FastAPI application. Initializes the app, CORS, static files, API routers, and starts the Uvicorn server.
*   **`backend/app/api/`**: Contains API routing modules.
    *   **`img_proc.py`**: Defines API endpoints for image processing, table detection, and handwritten text generation (e.g., `/detect_table_image`, `/gen_hw_image`).
*   **`backend/app/core/`**: Contains core business logic.
    *   **`cache.py`**: Implements caching mechanisms (likely SQLite-based).
    *   **`cam_controller.py`**: `CameraController` class for interacting with an Android device's camera via ADB.
    *   **`grbl_controller.py`**: `GRBLController` class for controlling a GRBL-based CNC machine.
    *   **`table_detect.py`**: `TableDetect` class for table detection in images (currently mocked, planned for Aliyun OCR).
    *   **`coor_converter.py`**: Handles coordinate transformations.
    *   **`handword_gen/`**: Logic for generating handwritten text images.
    *   **`sheet_model/`**: Models for different sheet types, including `SingleTable` for processing.
*   **`backend/app/services/`**: Service-layer modules.
    *   **`image_service.py`**: `ImageService` for saving uploaded images.
    *   **`table_service.py`**: `TableService` orchestrating table detection, image correction, and handwritten image generation.
*   **`backend/app/schemas/`**: Pydantic models for data validation.
    *   **`image_index.py`**: Defines the `ImageIndex` structure for cached items.
    *   **`table_info_struct.py`**: Defines structures for table-related API requests.
*   **`backend/app/static/`**: Directory for serving static files (e.g., uploaded images).
*   **`backend/app/cache_data/`**: Stores persistent cache data (e.g., `cache.db`).
*   **`backend/requirements.txt`**: Python dependencies for the backend.

### Frontend (`web/`)

The frontend provides the user interface for uploading images, editing table data, and viewing results.

*   **`web/src/App.vue`**: Main root Vue component, defining the overall application layout.
*   **`web/src/main.js`**: Entry point for the Vue.js application; initializes Vue, router, etc.
*   **`web/src/router/index.js`**: Configures client-side routing using `vue-router`.
*   **`web/src/api/img_proc.js`**: JavaScript functions for making API calls to backend image processing endpoints.
*   **`web/src/views/`**: Vue components representing different pages.
    *   **`Home.vue`**: Primary interactive page for document recognition, table editing, and handwritten image generation.
    *   **`About.vue`**, **`Contact.vue`**, **`Docs.vue`**: Static informational pages.
*   **`web/src/components/`**: Reusable Vue components (e.g., `Header.vue`).
*   **`web/src/utils/request.js`**: Utility for configuring Axios for API requests (base URL, interceptors).
*   **`web/public/index.html`**: Main HTML file for the SPA.
*   **`web/package.json`**: Defines frontend dependencies and project scripts.
*   **`web/vue.config.js`**: Configuration for Vue CLI (build process, dev server).
*   **`web/.env`**: Environment variables (e.g., `VUE_APP_BASE_API` for backend URL).

## 3. Project Progress

The project is in a **mid-to-late stage of development**. Core architectural structures for both backend and frontend are in place, and essential communication pathways have been established.

**Key Completed Areas:**

*   **Backend:**
    *   FastAPI application setup (server, routing, CORS).
    *   Image upload and basic serving capabilities.
    *   Functional interfaces for hardware control: `cam_controller.py` (Android camera via ADB) and `grbl_controller.py` (GRBL CNC via serial).
    *   Caching system using SQLite (`core/cache.py` and `cache_data/`).
    *   Service layer (`TableService`, `ImageService`) for orchestrating operations.
*   **Frontend:**
    *   Vue.js application structure with client-side routing.
    *   User interface for the main workflow in `Home.vue` (image upload, table data display, cell content editing).
    *   API integration module (`api/img_proc.js`) for communication with the backend.
*   **Overall:**
    *   The digital part of the workflow (upload -> detect (mocked) -> display -> edit -> generate digital handwritten preview) is largely functional.

**Areas Requiring Further Development or Integration:**

*   **Table Detection/OCR (`backend/app/core/table_detect.py`):**
    *   Currently **mocked** to read from a local JSON file. Integration with a live OCR service (e.g., Aliyun) or a robust local model is critical.
*   **Image Correction & Advanced Table Structuring (`backend/app/core/sheet_model/SingleTable.py`):**
    *   Relies on the `SingleTable` class, whose implementation details and completeness are not fully known from the provided codebase. This is important for handling real-world image distortions and complex table layouts.
*   **Handwritten Image Synthesis (`backend/app/core/handword_gen/`):**
    *   Relies on the `gen_handwriter_image` function, whose implementation details and quality of output are not fully known.
*   **Physical Output Automation (G-Code & GRBL Execution):**
    *   **G-Code Generation:** Logic to convert the final digital handwritten table into G-code commands suitable for the GRBL controller needs to be developed.
    *   **Backend API for GRBL Execution:** An API endpoint to trigger G-code execution via `grbl_controller.py` is missing.
    *   **Frontend UI for Physical Output:** Controls to initiate and monitor the physical writing process.
*   **Static Content Pages (Frontend):** Pages like Docs, About, Contact are placeholders and need actual content.
*   **Error Handling and Robustness:** Comprehensive error handling, input validation, and thorough testing are needed for a production-ready system.
*   **Calibration & Configuration:** UI and backend logic for camera and GRBL machine calibration, and potentially for handwriting style customization.

## 4. Core Code Explanation

Here are some key code snippets that illustrate the project's core functionalities:

### Backend Snippets

**Snippet 1: API Endpoint for Table Detection (Backend)**

*   **Purpose**: Defines the main backend API endpoint that receives an image, processes it for table detection, and returns structured data and image IDs.
*   **File**: `backend/app/api/img_proc.py`
*   **Code**:
    ```python
    @router.post(
        "/detect_table_image",
        summary="处理表格图片",
        description="接收用户上传的表格图片，进行校正和表格识别",
        status_code=status.HTTP_200_OK
    )
    async def detect_table_image(
        file: UploadFile = File(..., description="要处理的表格图片文件"),
        table_service: TableService = Depends(get_table_service)
    ) -> Dict[str, Any]:
        """
        处理表格图片接口
        
        接收图片文件，进行表格识别和校正，返回校正后的图片和表格数据
        """
        try:
            # 调用服务层处理表格图片
            result = await table_service.detect_table_image(file)
            return result
        except HTTPException as http_exc:
            # 如果服务层抛出的是 HTTPException，直接重新抛出
            raise http_exc
        except Exception as e:
            # 捕获其他意外错误
            print(f"API 层捕获到未知错误: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"发生意外错误: {e}",
            )
    ```
*   **Explanation**:
    This FastAPI endpoint (`/api/img_proc/detect_table_image`) handles POST requests for table image processing. It takes an `UploadFile` as input and uses dependency injection to get an instance of `TableService`. The core processing logic is delegated to `table_service.detect_table_image(file)`, which returns a dictionary containing image IDs and table data. The endpoint includes error handling to catch and return appropriate HTTP responses.

---

**Snippet 2: Core Orchestration Logic in `TableService` (Backend)**

*   **Purpose**: Shows a key part of the `TableService` where it orchestrates table detection, processing (using `SingleTable`), and caching of results.
*   **File**: `backend/app/services/table_service.py`
*   **Code**:
    ```python
    async def detect_table_image(self, file: UploadFile) -> Dict[str, Any]:
        # ... (initial validation and original image saving to cache) ...
            img_index = ImageIndex()
            img_index.original_image_name = file.filename
            
            img_index.original_image_key = uuid.uuid4().hex
            content = await file.read()
            cache = get_cache()
            cache.save_image(img_index.original_image_key, content)

            detector = TableDetect(img_index.original_image_key) 
            sheet_type = await detector.get_sheet_type()

            if sheet_type == "singlesheet":
                table_info = await detector.get_table_info()
                single_table = SingleTable(img_index.original_image_key, table_info)
                
                corrected_image = single_table.get_corrected_image()
                img_index.corrected_image_key = uuid.uuid4().hex
                cache.save_image_cv2(img_index.corrected_image_key, corrected_image)

                drawed_image = single_table.get_drawed_image()
                img_index.drawed_image_key = uuid.uuid4().hex
                cache.save_image_cv2(img_index.drawed_image_key, drawed_image)

                web_tdtr_data = single_table.get_web_tdtr_data()
                img_index.web_tdtr_data_key = uuid.uuid4().hex
                cache.save_json(img_index.web_tdtr_data_key, web_tdtr_data)
                
                # ... (saving corrected_table_info and img_index to cache) ...

                return {
                    "success": True,
                    "img_index_key": img_index_key, 
                    # ... other image IDs and data ...
                    "web_tdtr_data": web_tdtr_data,
                }
            # ... (else block for non-singlesheet types) ...
    ```
*   **Explanation**:
    This method within `TableService` coordinates the table detection process. It first saves the uploaded image to a cache. Then, it uses `TableDetect` (currently mocked) for initial table recognition. If a "singlesheet" is detected, it employs the `SingleTable` class (external) to perform image correction, generate a drawn overlay of the table, and extract structured table data for the web. Each artifact (original image, corrected image, drawn image, JSON data) is saved to the cache with unique keys, and an `ImageIndex` object tracking these keys is also cached. The method returns these keys and data to the API layer.

---

**Snippet 3: GRBL Pen Control (Hardware Interaction - Backend)**

*   **Purpose**: Illustrates how the `GRBLController` sends commands to the GRBL machine for pen up/down actions.
*   **File**: `backend/app/core/grbl_controller.py`
*   **Code**:
    ```python
    # ... (within GRBLController class) ...
    def _move_z(self, target_z):
        """内部函数，移动Z轴到指定绝对位置"""
        cmd = f"G90 G0 Z{target_z:.3f}" # G90: Absolute, G0: Rapid move
        response = self._send_grbl_command(cmd)
        if response and 'ok' in response[-1]:
            self.current_z = target_z 
            print(f"Z轴已移动到: {target_z:.3f}")
            return True
        print(f"Z轴移动失败。响应: {response}")
        return False

    def pen_down(self):
        """落笔操作"""
        print("执行落笔...")
        res = self._move_z(self.z_pen_down_value) 
        if res:
            self.is_pen_down = True
        return res

    def pen_up(self):
        """抬笔操作"""
        print("执行抬笔...")
        res = self._move_z(self.z_pen_up_value) 
        if res:
            self.is_pen_down = False
        return res
    ```
*   **Explanation**:
    The `_move_z` method constructs a G-code command (`G90 G0 Z...`) to move the Z-axis to an absolute position and sends it to the GRBL machine via `_send_grbl_command`. The `pen_down` and `pen_up` methods provide higher-level abstractions, calling `_move_z` with pre-configured Z-axis values (`self.z_pen_down_value`, `self.z_pen_up_value`) that correspond to the physical requirements for lowering or lifting the pen. It also updates an internal state `self.is_pen_down`.

---

### Frontend Snippets

**Snippet 4: API Call for Table Detection (Frontend to Backend Communication)**

*   **Purpose**: Shows how the frontend makes an API call to the backend to process an uploaded image.
*   **Files**: `web/src/api/img_proc.js` (API function) and `web/src/views/Home.vue` (usage)
*   **Code**:

    *In `web/src/api/img_proc.js`:*
    ```javascript
    import request from '@/utils/request' // Axios instance

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
    ```

    *In `web/src/views/Home.vue` (methods section):*
    ```javascript
    async handleFileChange(file) {
      // ... (file validation) ...
      try {
        const formData = new FormData();
        formData.append('file', file.raw); 
        this.loading = true;
        const result = await detectTableImage(formData); // API call
        
        const imgBaseUrl = process.env.VUE_APP_BASE_API + '/img_proc/image/';
        if (result.success && result.drawed_image_id) {
          this.img_index_key = result.img_index_key;
          this.previewImage = imgBaseUrl + result.drawed_image_id;
        } 
        if (result.success && result.web_tdtr_data) {
            this.detectResult.web_tdtr_data = result.web_tdtr_data;
        }
        this.$message.success('识别成功！');
      } catch (error) { /* ... */ } 
      finally { this.loading = false; }
    }
    ```
*   **Explanation**:
    The `detectTableImage` function in `img_proc.js` uses an Axios instance (`request`) to send a POST request with `FormData` (containing the image) to the backend's `/img_proc/detect_table_image` endpoint. In `Home.vue`, the `handleFileChange` method prepares this `FormData` and calls `detectTableImage`. Upon receiving a successful response (`result`), it updates the component's state with the image URLs (for preview) and table data returned from the backend, triggering UI updates.

---

**Snippet 5: Frontend Table Data Rendering and Editing Logic (Frontend)**

*   **Purpose**: Shows how `Home.vue` renders the editable table from data received from the backend and handles user edits.
*   **File**: `web/src/views/Home.vue` (template and script)
*   **Code**:

    *Template section:*
    ```html
    <div v-if="detectResult.web_tdtr_data !== null" class="web-tdtr-table-container">
      <h3>表格识别结果</h3>
      <table class="editable-table">
        <tr v-for="(row, rowIndex) in detectResult.web_tdtr_data.tdtr_cells" :key="rowIndex">
          <td v-for="(cell, colIndex) in getVisibleCells(row)" 
            :key="colIndex"
            :rowspan="cell.rowSpan" :colspan="cell.colSpan"
            :style="{ textAlign: cell.textAlign }"
            >
              <span v-if="cell.isEditable" @click="showEditDialog(cell)">
                <!-- Display cell.text, potentially cell.originalText -->
                <div v-if="cell.originalText" :style="{ color: 'gray' }">{{ cell.originalText }}</div>
                <div>{{ cell.text }}</div>
              </span>
              <span v-else>{{ cell.originalText }}</span>
          </td>
        </tr>
      </table>
    </div>
    ```

    *Script section (methods):*
    ```javascript
    methods: {
      getVisibleCells(row){ 
        return row.filter(cell => cell.isValid == true);
      },
      showEditDialog(cell) { 
        // Dynamically creates a modal for editing cell.text and cell.textAlign.
        // On confirmation, it directly modifies the 'text' and 'textAlign' 
        // properties of the 'cell' object within 'this.detectResult.web_tdtr_data'.
      },
      async saveTableData() { 
        // ...
        const requestData = { 
          ...this.detectResult.web_tdtr_data, // Includes modified tdtr_cells
          img_index_key: this.img_index_key 
        };
        const result = await genHwImage(requestData); // Send edited data
        // ...
      }
    }
    ```
*   **Explanation**:
    The template iterates through `detectResult.web_tdtr_data.tdtr_cells` (populated from backend response) to render the table. Editable cells (`cell.isEditable`) have a click listener that calls `showEditDialog(cell)`. This method (using direct DOM manipulation) allows users to modify `cell.text` and `cell.textAlign`. Since these properties are part of Vue's reactive data (`detectResult.web_tdtr_data`), changes automatically update the displayed table. The `saveTableData` method then sends this (potentially modified) `detectResult.web_tdtr_data` back to the backend to generate the handwritten image.
```
