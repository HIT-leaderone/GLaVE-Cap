import numpy as np
import cv2
import matplotlib.pyplot as plt
import json
import os
import random

# 计算 mask 面积的阈值
AREA_THRESHOLD = 16 * 16  # 面积过滤的最小阈值
def get_contours_for_id(mask, object_id):
    """
    提取单个物体的轮廓。
    :param mask: 二维数组，物体的id，背景为0
    :param object_id: 当前物体的id
    :return: 轮廓列表
    """
    # 为当前物体创建一个二值掩码
    binary_mask = np.zeros_like(mask, dtype=np.uint8)
    binary_mask[mask == object_id] = 255
    # 提取轮廓
    contours, _ = cv2.findContours(binary_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    return contours


def calculate_id_area(mask, object_id):
    """
    计算单个物体的面积。
    """
    return np.sum(mask == object_id)


def calculate_contrast(color1, color2):
    """
    计算两个颜色之间的亮度对比度。
    使用公式：对比度 = |亮度1 - 亮度2|
    亮度 = 0.299 * R + 0.587 * G + 0.114 * B
    """
    brightness1 = 0.299 * color1[2] + 0.587 * color1[1] + 0.114 * color1[0]
    brightness2 = 0.299 * color2[2] + 0.587 * color2[1] + 0.114 * color2[0]
    return abs(brightness1 - brightness2)


def calculate_contrast_color(image, contours):
    """
    生成与轮廓内像素颜色对比度较大的随机颜色。
    """
    mask = np.zeros(image.shape[:2], dtype=np.uint8)
    # 在掩码上绘制当前轮廓
    cv2.drawContours(mask, contours, -1, 255, thickness=cv2.FILLED)

    # 计算轮廓内像素的平均颜色
    mean_color = cv2.mean(image, mask=mask)[:3]  # 忽略 alpha 通道
    avg_color = tuple(map(int, mean_color))  # 转换为整数

    # 随机生成一个与平均颜色对比度较大的颜色
    while True:
        random_color = tuple(random.randint(0, 255) for _ in range(3))
        contrast = calculate_contrast(avg_color, random_color)
        if contrast > 125:  # 125 是对比度阈值，可根据需要调整
            break

    return random_color

def find_nearest_point(mask):
       # 质心方法计算理论中心点
       rows, cols = np.where(mask == 1)
       if len(rows) == 0:
           return None  # 没有目标区域
       center_row = np.mean(rows)
       center_col = np.mean(cols)

       # 找到最近点
       distances = (rows - center_row) ** 2 + (cols - center_col) ** 2
       nearest_index = np.argmin(distances)
       nearest_row, nearest_col = rows[nearest_index], cols[nearest_index]
       return (nearest_row, nearest_col)

def add_text_with_background(masked_image, text, pos, font_face=cv2.FONT_HERSHEY_SIMPLEX, font_scale=0.4, font_thickness=1, bg_color=(0, 0, 0), bg_alpha=0.5):
    # Get the width and height of the text box
    (text_width, text_height), baseline = cv2.getTextSize(text, font_face, font_scale, font_thickness)

    # Calculate the rectangle coordinates
    x, y = pos
    bg_rect_start = (int(x - text_width / 2), int(y - (text_height + baseline) / 2))
    bg_rect_end = (int(x + text_width / 2), int(y + (text_height + baseline) / 2))

    # Draw the rectangle (filled) on the overlay
    cv2.rectangle(masked_image, bg_rect_start, bg_rect_end, bg_color, -1)

    # Add the overlay with alpha blending
    cv2.addWeighted(masked_image, bg_alpha, masked_image, 1 - bg_alpha, 0, masked_image)

    # Put the text itself
    text_color = (255 - bg_color[0], 255 - bg_color[1], 255 - bg_color[2])
    cv2.putText(masked_image, text, (int((x - text_width / 2)), int(y + (text_height) / 2)), font_face, font_scale, text_color, font_thickness, lineType=cv2.LINE_AA)

color_map = {}

def process_single_id(image, mask, object_id, masked_image):
    """
    处理单个物体的轮廓、绘制轮廓和保存。
    """
    # print(f"   Id = {object_id}")
    # 计算当前物体的面积
    area = calculate_id_area(mask, object_id)
    # 如果物体的面积小于阈值，则跳过
    if area < AREA_THRESHOLD:
        # print(f"Object ID {object_id} skipped due to small area ({area} < {AREA_THRESHOLD})")
        return False
    # 获取轮廓
    contours = get_contours_for_id(mask, object_id)
    # 如果当前ID没有轮廓，则跳过
    if len(contours) == 0:
        return False
    # 绘制轮廓并随机指定颜色
    if object_id not in color_map:
        color_map[object_id] = calculate_contrast_color(image, contours)
    color = color_map[object_id]
    for contour in contours:
        cv2.drawContours(masked_image, [contour], -1, color, thickness=1)
    [pos_x, pos_y] = find_nearest_point(mask == object_id)
    # print(f"pos = {pos_x}, {pos_y}")
    add_text_with_background(masked_image, str(object_id), [pos_y, pos_x], bg_color = color)
    return True


def process_image_and_mask(image_path, mask, frame_id, output_base, json_data, json_path):
    # print(f"Processing: {image_path}")
    image = cv2.imread(image_path)
    masked_image = image.copy()
    # 获取 mask 中的所有唯一 id
    unique_ids = np.unique(mask)
    unique_ids = unique_ids[unique_ids != 0]  # 排除背景
    # print(f"Detected IDs: {unique_ids}")
    object_list = []
    for object_id in unique_ids:
        find_counter = process_single_id(image, mask, object_id, masked_image)
        if find_counter != False:
            object_list.append(str(object_id))
    
    del_list = []
    for key, value in json_data["labels"].items():
        if key not in object_list:
            del_list.append(key)
    for key in del_list:
        del json_data["labels"][key]
    output_file = f'{output_base}/masked_number/{frame_id}.jpg'
    cv2.imwrite(output_file, masked_image)
    with open(json_path, 'w', encoding='utf-8') as file:
        json.dump(json_data, file, ensure_ascii=False, indent=4)
    # print(f"Output to {output_file}")

def process_id(video_filename, input_path, mask_base):
    print(f"Processing ID: {video_filename}")
    video_id = video_filename.split('.')[0]
    video_path = os.path.join(input_path, video_filename)
    key_list_path = os.path.join(video_path, "key_list.json")  # 获取完整的文件路径

    # 加载 key_list
    with open(key_list_path, 'r') as f:
        key_list = json.load(f)
    # print(key_list)
    frame_list = []
    for image_filename in os.listdir(video_path):
        frame_id, ext = image_filename.split(".")
        if ext == "json": continue
        frame_list.append(int(frame_id))
    frame_list = sorted(frame_list)
    
    print("frame_list=", len(frame_list))
    for frame_id in frame_list:
        image_path = os.path.join(video_path, f"{frame_id}.jpg")

        # 输出目录，确保其存在
        output_base = f"{mask_base}/{video_id}"
        masked_colorful_path = os.path.join(output_base, "masked_number")
        if not os.path.exists(masked_colorful_path):
            os.makedirs(masked_colorful_path)
        
        # 加载对应帧的 mask
        mask_path = f"{mask_base}/{video_id}/mask_data/mask_{key_list[int(frame_id)]}.npy"
        mask = np.load(mask_path)
        
        json_path = f"{mask_base}/{video_id}/json_data/mask_{key_list[int(frame_id)]}.json"
        with open(json_path, 'r') as file:
            original_dict = json.load(file)

        # 处理该图像及其 mask
        print("frame_id=",frame_id)
        json_dir = f"{mask_base}/{video_id}/json_data_modify"
        if not os.path.exists(json_dir): os.makedirs(json_dir)
        save_file = f"{mask_base}/{video_id}/json_data_modify/mask_{key_list[int(frame_id)]}.json"
        process_image_and_mask(image_path, mask, int(key_list[int(frame_id)]), output_base, original_dict, save_file)
        #     break
        # break