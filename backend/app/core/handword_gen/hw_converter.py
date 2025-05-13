from handright import Template, handwrite
import string
from PIL import Image, ImageDraw, ImageFont  # 新增Pillow导入
import json
import cv2
import numpy as np

def calculate_text_positions_with_wrap(cell_points, text, font_size, h_align='left', v_align='top', cn_char_spacing=0, en_char_spacing=0, line_spacing=5, margin=3):
    """
    计算单元格中每个字符的左上角坐标，支持自动换行
    
    参数:
    cell_points -- 单元格的四个顶点坐标，格式为 [{'x': x1, 'y': y1}, {'x': x2, 'y': y2}, ...]
                   顺序为：左上、左下、右下、右上
    text -- 需要填写的文字
    font_size -- 文字大小
    h_align -- 水平对齐方式，可选值：'left', 'center', 'right'
    v_align -- 垂直对齐方式，可选值：'top', 'middle', 'bottom'
    cn_char_spacing -- 中文字符间距，默认为0
    en_char_spacing -- 英文和数字字符间距，默认为0
    line_spacing -- 行间距，默认为5
    margin -- 文本与单元格边界的边距，默认为3
    返回:
    positions -- 每个字符的左上角坐标列表，格式为 [(x1, y1, char), ...]
    """
    # 计算单元格的宽度和高度
    width = max(
        abs(cell_points[0]['x'] - cell_points[1]['x']),  # 上边
        abs(cell_points[2]['x'] - cell_points[3]['x'])   # 下边
    )
    height = max(
        abs(cell_points[0]['y'] - cell_points[3]['y']),  # 左边
        abs(cell_points[1]['y'] - cell_points[2]['y'])   # 右边
    )
    
    # 判断字符是否为符号的函数
    def is_punctuation(char):
        if char in ['“','”']:
            #print(char,"true")
            return True

        # 特殊处理一些可能被遗漏的符号
        if char in ['“','”','"', '"', '"', ''', ''', '「', '」', '『', '』', '《', '》', '（', '）', '【', '】', '—', '–', '-', '…']:
            #print(char,"true")
            return True

        # 中文标点符号范围（扩展范围以确保包含所有中文标点）
        if '\u3000' <= char <= '\u303f' or '\uff00' <= char <= '\uffef':
            #print(char,"true")
            return True
        
        # 英文标点符号
        #print(char, char in string.punctuation)
        return char in string.punctuation
    
    # 判断字符是否为中文的函数
    def is_chinese(char):
        # 中文字符范围
        if '\u4e00' <= char <= '\u9fff':
            return True
        # 不将中文标点符号视为中文字符，而是作为独立的符号处理
        return False
    
    # 计算一行文本的实际宽度
    def calculate_line_width(line):
        width = 0
        for i, char in enumerate(line):
            # 计算字符宽度
            if is_chinese(char):
                char_width = font_size * 0.8
            elif is_punctuation(char):
                char_width = font_size
            else:
                char_width = font_size * 0.5
            
            # 所有符号前面都加间距（除非是行首）
            if i > 0 and is_punctuation(char):
                width += 2  # 符号前增加2px间距
            
            width += char_width
            
            # 所有符号后面都加间距（除非是行尾）
            if is_punctuation(char) and i < len(line) - 1:
                width += -1  # 符号后增加2px间距
            # 如果不是最后一个字符，添加正常字间距
            elif i < len(line) - 1:
                next_char = line[i + 1]
                # 如果下一个字符是符号，不添加额外间距（因为符号前会添加间距）
                if not is_punctuation(next_char):
                    if is_chinese(char) == is_chinese(next_char):
                        # 同类型字符之间使用对应的间距
                        width += cn_char_spacing if is_chinese(char) else en_char_spacing
                    else:
                        # 中英文之间使用较大的间距
                        width += max(cn_char_spacing, en_char_spacing)
        return width

    # 计算每行可容纳的最大字符数（考虑边距）
    test_line = "测" * 100  # 使用中文测试，因为中文字符宽度较大
    max_width = width - 2 * margin
    max_chars_per_line = 1
    current_width = 0
    
    while current_width < max_width and max_chars_per_line < len(test_line):
        current_width = calculate_line_width(test_line[:max_chars_per_line])
        if current_width < max_width:
            max_chars_per_line += 1
        else:
            break
    
    # 分行处理文本
    lines = []
    current_line = ""
    current_width = 0
    
    for char in text:
        if char == '\n':  # 处理换行符
            lines.append(current_line)
            current_line = ""
            current_width = 0
        else:
            # 计算添加当前字符后的宽度
            test_width = calculate_line_width(current_line + char)
            if test_width <= max_width:
                current_line += char
                current_width = test_width
            else:
                lines.append(current_line)
                current_line = char
                current_width = calculate_line_width(char)
    
    # 添加最后一行
    if current_line:
        lines.append(current_line)

    # 计算文本总高度
    total_text_height = len(lines) * font_size + (len(lines) - 1) * line_spacing
    
    # 根据垂直对齐方式计算起始 y 坐标
    if v_align == 'top':
        start_y = cell_points[0]['y'] + margin
    elif v_align == 'bottom':
        start_y = max(cell_points[0]['y'] + height - total_text_height - margin, cell_points[0]['y'] )
    else:  # 垂直居中
        start_y = max(cell_points[0]['y'] + (height - total_text_height) / 2, cell_points[0]['y'])
    
    # 计算每个字符的位置
    positions = []
    for line_idx, line in enumerate(lines):
        # 计算当前行的宽度
        line_width = calculate_line_width(line)
        
        # 根据水平对齐方式计算起始 x 坐标
        if h_align == 'left':
            start_x = cell_points[0]['x'] + margin
        elif h_align == 'right':
            start_x = cell_points[0]['x'] + width - line_width - margin
        else:  # 居中
            start_x = cell_points[0]['x'] + (width - line_width) / 2
        
        # 当前行的 y 坐标
        y = start_y + line_idx * (font_size + line_spacing)
        
        # 计算当前行每个字符的位置
        current_x = start_x
        for i, char in enumerate(line):
            # 所有符号前面都加间距（除非是行首）
            if i > 0 and is_punctuation(char):
                current_x += 2  # 符号前增加2px间距
                
            positions.append([int(current_x), int(y), char])
            
            # 计算字符宽度
            if is_chinese(char):
                char_width = font_size * 0.8
            elif is_punctuation(char):
                char_width = font_size
            else:
                char_width = font_size * 0.5
            
            current_x += char_width
            # 所有符号后面都加间距（除非是行尾）
            if is_punctuation(char) and i < len(line) - 1:
                current_x += -1  # 符号后增加1px间距
            # 如果不是最后一个字符，添加正常字间距
            elif i < len(line) - 1:
                next_char = line[i + 1]
                # 如果下一个字符是符号，不添加额外间距（因为符号前会添加间距）
                if not is_punctuation(next_char):
                    if is_chinese(char) == is_chinese(next_char):
                        # 同类型字符之间使用对应的间距
                        current_x += cn_char_spacing if is_chinese(char) else en_char_spacing
                    else:
                        # 中英文之间使用较大的间距
                        current_x += max(cn_char_spacing, en_char_spacing)
    
    return positions

def gen_handwriter_image(tr_tables_info, tr_word_info, input_table_info, tr_img_cv2):
    """
     tr_tables_info: data['data']['prism_tablesInfo'][0]['cellInfos']  已经经过透视变换
     tr_word_info: data['data']['prism_wordInfo']  已经经过透视变换
     input_table_info: 前端传入的tableInfo
     tr_img_cv2: 透视变换后的图片
    """

    fs = 16
    cv2_image_rgb = cv2.cvtColor(tr_img_cv2, cv2.COLOR_BGR2RGB)
    pil_image = Image.fromarray(cv2_image_rgb)

     # 遍历每个单元格
    for cell in tr_tables_info:
        # 获取单元格ID
        cell_id = cell['tableCellId']
        
        # 在text_data中查找对应的文本内容和对齐方式
        text_content = None
        text_align = None
        v_align = None
        for row in input_table_info:
            for item in row:
                if item['tableCellId'] == cell_id and item['isValid'] and item['text']:
                    
                    text_content = item['text']
                    text_align = item['textAlign'].split()[0]  # 获取水平对齐方式
                    v_align = item['textAlign'].split()[1] if len(item['textAlign'].split()) > 1 else 'middle'  # 获取垂直对齐方式
                    break
            if text_content:
                break

        if text_content:
            
            points = cell['pos']
            
            if cell["word"]:
                word_height = 8
                for word in tr_word_info:
                    if word['tableCellId'] == cell_id:
                        word_height += word["width"]
                        break

                points[0]["y"],points[1]["y"] = points[0]["y"]+word_height , points[1]["y"]+word_height  #空出word的位置
            
            # 计算文字位置
            text_positions = calculate_text_positions_with_wrap(
                points,
                text_content,
                fs,  # 字体大小
                h_align=text_align,
                v_align=v_align,
                cn_char_spacing=0,  # 中文字符间距
                en_char_spacing=0,  # 英文字符间距（中英文之间会使用2）
                line_spacing=2,
                margin=5
            )

            # 为每个字符创建手写效果
            font_path = "F:/typewriter/Handright-master/Handright-master/tests/fonts/font.ttf"
            # 放大倍数
            scale_factor = 12
            template = Template(
                background=Image.new(mode="RGBA", size=(fs*(scale_factor+1), fs*(scale_factor+1)), color=(0, 0, 0, 0)),
                font=ImageFont.truetype(font_path, size=fs*scale_factor),
                line_spacing=fs*scale_factor + 4,
                fill=(0, 0, 0)
            )
            
            # 绘制文字
            for [x, y, char] in text_positions:
                if char != '\n':
                    handwritten = list(handwrite(char, template))[0]
                    # 缩小到目标尺寸
                    handwritten = handwritten.resize(
                        (fs, fs), 
                        Image.Resampling.LANCZOS  # 高质量缩小
                    )
                    pil_image.paste(handwritten, (x, y), handwritten)

    # 将PIL图像转换回OpenCV格式
    transformed_img = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
    return transformed_img


if __name__ == "__main__":
    corrected_image_path = r"F:\typewriter\AutoWriter\corrected_img.jpg"
    corrected_table_path = r"F:\typewriter\AutoWriter\corrected_table.json"
    table_filled_path = r"F:\typewriter\AutoWriter\table-data-filled.json"

    with open(corrected_table_path, 'r', encoding='utf-8') as file:
        corrected_table_info = json.load(file)

    with open(table_filled_path, 'r', encoding='utf-8') as file:
        table_filled_info = json.load(file)    

    tr_tables_info = corrected_table_info['data']['prism_tablesInfo'][0]['cellInfos']
    tr_word_info = corrected_table_info['data']['prism_wordsInfo']
    table_filled_info = table_filled_info["tdtr_cells"]
    img = gen_handwriter_image(tr_tables_info,tr_word_info,table_filled_info,corrected_image_path)
    cv2.imshow('Table', img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()